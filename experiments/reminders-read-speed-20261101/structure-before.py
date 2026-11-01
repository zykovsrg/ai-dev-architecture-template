#!/usr/bin/env python3
"""Сверка только подтверждённых структурных связей; задачи не записываются."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def safe_path(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('unsafe_path: ' + str(path))
    return path


def atomic_write(path, data):
    path = safe_path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        name = handle.name
        handle.write(data.encode('utf-8'))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(name, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def standard_allowlist(config):
    selected = safe_path(config.get('standard_allowlist_file', config['allowlist_file']))
    if 'standard_allowlist_file' in config and selected != safe_path(config['allowlist_file']).parent / 'reminders-standard-allowlist.json':
        raise ValueError('unsafe_standard_allowlist')
    return str(selected)


def migration_pending(hub, config):
    spec = importlib.util.spec_from_file_location('structure_migration', Path(__file__).with_name('reminders_project_lists.py'))
    if not Path(spec.origin).exists(): return set(config.get('project_list_migrations_pending', {})) | set(config.get('archive_pending', {}).get('projects', []))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.pending_projects(hub, config) | set(config.get('archive_pending', {}).get('projects', []))


class StructureNative:
    """Читает разрешённую структуру; в явном двустороннем режиме разрешает узкие переносы."""
    def __init__(self, config):
        self.config = config
    def cancellation_status(self, args):
        sync = cancellation_sync_module()
        return sync.Native(self.config).call('hub_cancel_status', args)
    def call(self, tool, args):
        if tool not in ({'list_lists', 'find_reminders', 'manage_list', 'update_reminder', 'get_reminder'} if self.config.get('structure',{}).get('bidirectional') else {'list_lists', 'find_reminders', 'get_reminder'}):
            raise ValueError('structure_read_only')
        env = dict(os.environ, HUB_REMINDERS_ALLOWED_LISTS_FILE=standard_allowlist(self.config),
                   HUB_REMINDERS_ALLOWED_GROUPS_FILE=self.config['structure']['groups_allowlist_file'])
        env.pop('HUB_REMINDERS_ALLOWED_GROUP_IDS_FILE',None)
        pin=self.config['structure'].get('group_ids_allowlist_file')
        if pin:env['HUB_REMINDERS_ALLOWED_GROUP_IDS_FILE']=str(safe_path(pin))
        binary = self.config['binary']
        runner = lambda name, values: subprocess.run([binary, 'call', name, json.dumps(values)], env=env, capture_output=True, text=True, timeout=50)
        reads = sys.modules.get('hub_reminders_reads') or cancellation_sync_module().reads_module()
        result = reads.call(binary, env, tool, args, runner) if reads else runner(tool, args)
        if result.returncode:
            raise RuntimeError('structure_native_failed: ' + result.stderr[:500])
        value = json.loads(result.stdout[result.stdout.index('{'):])
        if value.get('error') or value.get('isError'):
            raise ValueError('structure_native_error: ' + str(value)[:500])
        return value


def fresh_reads():
    reads = sys.modules.get('hub_reminders_reads')
    if reads:
        reads.refresh()


def retired_parent_read_ids(config):
    return {binding['retired_parent']['id'] for binding in config['projects'].values()
            if binding.get('retired_parent')}


def snapshot(native, roles, names, detailed=False, detailed_ids=(), include_groups=False):
    value = native.call('list_lists', {})
    native_groups=value.get('groups',[])
    if (detailed or include_groups) and (not isinstance(native_groups,list) or any(not isinstance(g,dict) or not g.get('id') or not isinstance(g.get('name'),str) for g in native_groups) or len({g['id'] for g in native_groups})!=len(native_groups)):
        raise ValueError('invalid_native_groups')
    lists = {}
    for row in value['lists']:
        lid = row.get('id')
        if lid in lists or not lid or not isinstance(row.get('name'), str):
            raise ValueError('duplicate_or_invalid_list')
        # Никакие неизвестные списки не становятся разрешёнными из-за ответа приложения.
        if row['name'] not in names and lid not in names:
            raise ValueError('unallowed_list_metadata')
        if 'group_id' not in row:
            raise ValueError('missing_group_metadata')
        if row['name'] in {v['name'] for v in lists.values()}:
            raise ValueError('ambiguous_list_name')
        lists[lid] = row
    if set(roles) - set(lists):
        raise ValueError('missing_allowed_list')
    if set(lists) != set(roles):
        raise ValueError('unconfirmed_list_role')
    reminders = {}
    for lid in sorted(roles):
        value = native.call('find_reminders', {'list': lid, 'include_completed': True, 'limit': 500})
        rows = value['reminders']
        if value.get('more') or value.get('has_more') or len(rows) > 500:
            raise ValueError('incomplete_reminder_snapshot')
        if 'count' in value and value['count'] != len(rows):
            raise ValueError('incomplete_reminder_snapshot')
        for row in rows:
            if row.get('list_id', lid) != lid or row.get('list', lists[lid]['name']) != lists[lid]['name']:
                raise ValueError('foreign_list_in_snapshot')
            if not row.get('id') or not row.get('version') or not isinstance(row.get('title'), str):
                raise ValueError('invalid_reminder_snapshot_row')
            if row['id'] in reminders:
                raise ValueError('duplicate_reminder')
            if detailed or row['id'] in detailed_ids:
                detail=native.call('get_reminder',{'id':row['id']})
                if detail.get('id')!=row['id'] or detail.get('version')!=row['version'] or detail.get('list_id')!=lid:
                    raise ValueError('structure_snapshot_changed')
                row=detail
            reminders[row['id']] = dict(row, list_id=lid)
    if detailed:
        for rid,row in reminders.items():
            if 'subtasks' in row:
                summary=row['subtasks']
                actual={cid for cid,child in reminders.items() if child.get('parent_id')==rid}
                if not isinstance(summary,list) or any(not isinstance(child,dict) or not child.get('id') for child in summary) or len(summary)!=len({child['id'] for child in summary}) or {child['id'] for child in summary}!=actual:
                    raise ValueError('incomplete_project_tree')
    # Только значимые сведения; часы и подсчитанные счётчики не влияют на идентичность снимка.
    result={'lists': {lid:{k:row[k] for k in ('id','name','group_id','account_id') if k in row} for lid,row in lists.items()}, 'reminders': reminders}
    if detailed or include_groups:
        group_keys=('id','name','account_id') if include_groups else ('id','name')
        result['groups']={g['id']:{k:g[k] for k in group_keys if k in g} for g in native_groups}
    return result


def load_groups(text):
    groups = {}
    for match in re.finditer(r'^## ([a-z0-9-]+)\n(.*?)(?=^## |\Z)',text,re.M|re.S):
        gid, body = match.groups()
        fences = re.findall(r'^```yaml\n(.*?)^```$', body, re.M|re.S)
        if len(fences)!=1:
            raise ValueError('invalid_archiproject_entry')
        fields = {}
        for line in fences[0].splitlines():
            key, sep, val = line.partition(':')
            if not sep or key in fields:
                raise ValueError('invalid_archiproject_fields')
            fields[key]=val.strip()
        if gid in groups or fields.get('id')!=gid or fields.get('kind')!='group' or not fields.get('name') or fields.get('status') not in {'active','paused','archived','missing','registration-pending'}:
            raise ValueError('invalid_archiproject_entry')
        groups[gid]=dict(parent=fields.get('parent') or None,status=fields['status'])
    validate_groups(groups)
    return groups


def validate_groups(groups):
    for gid in groups:
        seen=set()
        current=gid
        while current is not None:
            if current not in groups:raise ValueError('unknown_archiproject_parent')
            if current in seen:raise ValueError('archiproject_cycle')
            seen.add(current)
            if len(seen)>3:raise ValueError('archiproject_depth')
            current=groups[current]['parent']



def archive_module(config=None):
    path = safe_path(Path(__file__).absolute().with_name('reminders_archive.py'))
    if not path.exists():
        if config and (config.get('archive_pending') or any(b.get('archive') for b in config['projects'].values())):
            raise ValueError('archive_support_missing')
        return None
    spec = importlib.util.spec_from_file_location('reminders_archive_support', path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def registry_cards(hub, text):
    cards={}
    for match in re.finditer(r'^## ([a-z0-9-]+)\n(.*?)(?=^## |\Z)',text,re.M|re.S):
        pid,body=match.groups()
        if pid in cards:raise ValueError('ambiguous_registry')
        statuses=re.findall(r'^Status: (.+)$',body,re.M)
        if statuses!=['active']:continue
        paths=re.findall(r'^Path: (.+)$',body,re.M)
        cardpaths=re.findall(r'^Card: (.+)$',body,re.M)
        if len(paths)!=1 or len(cardpaths)!=1:raise ValueError('ambiguous_registry')
        project=safe_path(paths[0])
        card=safe_path(hub/cardpaths[0])
        if project.parent!=hub/'projects' or not project.is_dir() or card.parent!=hub/'ai/project-cards' or not card.is_file():
            raise ValueError('unsafe_registered_card')
        cards[pid]=card
    return cards


def primary_group(text,groups):
    lines=[line for line in text.splitlines() if line.lstrip().startswith('primary_archiproject')]
    if not lines:return 'none'
    if len(lines)!=1 or not re.fullmatch(r'primary_archiproject: [a-z0-9]+(?:-[a-z0-9]+)*',lines[0]):
        raise ValueError('invalid_project_card')
    group=lines[0].partition(': ')[2]
    if group!='none' and group not in groups:
        raise ValueError('invalid_project_card')
    return group


def replace_primary(text,group):
    if re.search(r'^primary_archiproject: ',text,re.M):
        return re.sub(r'^primary_archiproject: .+$','primary_archiproject: '+group,text,count=1,flags=re.M)
    return text+('' if not text or text.endswith('\n') else '\n')+'primary_archiproject: '+group+'\n'


def card_group(text,pid,groups):
    ids=re.findall(r'^Project ID: (.+)$',text,re.M)
    statuses=re.findall(r'^Status: (.+)$',text,re.M)
    primary=primary_group(text,groups)
    if ids!=[pid] or statuses!=['active']:
        raise ValueError('invalid_project_card')
    return primary


def subgroup_scope(hub, registry_text, groups, gid, originals):
    descendants={gid}
    while True:
        expanded=descendants|{g for g,v in groups.items() if v['parent'] in descendants}
        if expanded==descendants:break
        descendants=expanded
    affected=[]
    seen=set()
    for match in re.finditer(r'^## ([a-z0-9-]+)\n(.*?)(?=^## |\Z)',registry_text,re.M|re.S):
        pid,body=match.groups()
        statuses=re.findall(r'^Status: (.+)$',body,re.M)
        paths=re.findall(r'^Path: (.+)$',body,re.M)
        cardpaths=re.findall(r'^Card: (.+)$',body,re.M)
        if pid in seen or len(statuses)!=1 or len(paths)!=1 or len(cardpaths)!=1:
            raise ValueError('incomplete_subgroup_scope')
        seen.add(pid)
        project=safe_path(paths[0])
        card=safe_path(hub/cardpaths[0])
        if project.parent!=hub/'projects' or card.parent!=hub/'ai/project-cards' or not project.is_dir():
            raise ValueError('incomplete_subgroup_scope')
        originals[card]=card.read_text()
        text=originals[card]
        ids=re.findall(r'^Project ID: (.+)$',text,re.M)
        state=re.findall(r'^Status: (.+)$',text,re.M)
        primary=[primary_group(text,groups)]
        if ids!=[pid] or state!=statuses:
            raise ValueError('incomplete_subgroup_scope')
        if primary[0] in descendants:affected.append(pid)
    return sorted(affected)


def pending_structure_projects(hub,config):
    structure=config.get('structure',{})
    active=structure.get('outgoing_intent_sha256')
    completed=structure.get('outgoing_completed_sha256')
    if active and active!=completed:return sorted(config['projects'])
    if not structure.get('journal_file'):return []
    try:
        relative=Path(structure['journal_file'])
        if relative.is_absolute() or '..' in relative.parts or relative.parent!=Path('ai'):
            return sorted(config['projects'])
        journal=safe_path(Path(hub)/relative)
        if journal.exists():
            value=json.loads(journal.read_text())
            if active and active==completed and {'config','originals','snapshot'}<=set(value):
                payload={key:value[key] for key in ('config','originals','snapshot')}
                digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                if digest==active:return []
            if value.get('status')!='complete' or value.get('version')==2:return sorted(config['projects'])
        return []
    except (OSError,ValueError,KeyError):
        return sorted(config['projects'])


def remote_group(row, structure, groups):
    if 'group_id' not in row:raise ValueError('missing_group_metadata')
    native_id=row['group_id']
    if native_id is None:return 'none'
    gid=structure['native_groups'].get(native_id)
    if gid not in groups or groups[gid]['status']!='active':raise ValueError('unknown_native_group')
    return gid


def three_way(current, baseline, remote):
    if current!=baseline and remote!=current:
        raise ValueError('structure_two_sided_conflict')
    return remote


def identity_owner(notes, config, parent_project=None):
    lines=(notes or '').splitlines()
    marked=[x for x in lines if x.lstrip().startswith(('Хаб:','Hub Task ID:','Hub project:','--- Hub metadata','--- /Hub metadata'))]
    if not marked:return None
    if parent_project and marked==['Hub project: '+parent_project]:return parent_project
    compact=[x for x in marked if x.startswith('Хаб: ')]
    if len(marked)==1 and len(compact)==1 and re.fullmatch(r'Хаб: [0-9a-f]{12}',compact[0]):
        owners=[pid for pid,binding in config['projects'].items() for tid in binding.get('tasks',{}) if hashlib.sha256((pid+'\0'+tid).encode()).hexdigest()[:12]==compact[0][5:]]
        if len(owners)==1:return owners[0]
    pids=[x[13:] for x in marked if x.startswith('Hub project: ')]
    tids=[x[13:] for x in marked if x.startswith('Hub Task ID: ')]
    if len(marked)==4 and len(pids)==len(tids)==1 and marked[0]=='--- Hub metadata ---' and marked[-1]=='--- /Hub metadata ---' and tids[0] in config['projects'].get(pids[0],{}).get('tasks',{}):
        return pids[0]
    raise ValueError('foreign_identity')


def retired_parent_ids(config, snap):
    retired = set()
    for binding in config['projects'].values():
        receipt = binding.get('retired_parent')
        if receipt:
            row = snap['reminders'].get(receipt.get('id'))
            if row is None and binding.get('retired_parent_cleanup'):
                spec = importlib.util.spec_from_file_location('structure_old_list_cleanup', Path(__file__).with_name('reminders_old_list_cleanup.py'))
                cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)
                if cleanup.retired_parent_cleaned(None, binding):
                    retired.add(receipt['id'])
                    continue
            if (binding.get('layout') != 'project_list' or not row or
                    row != receipt.get('snapshot') or row['list_id'] != receipt.get('list_id') or
                    row.get('parent_id') is not None):
                raise ValueError('retired_project_parent_changed')
            retired.add(row['id'])
    return retired


def validate_project_ownership(pid, rows, config):
    """UUID сохраняет владельца и без служебной подписи в заметке."""
    foreign = set()
    for owner, binding in config['projects'].items():
        if owner == pid:
            continue
        if binding.get('parent_id'):
            foreign.add(binding['parent_id'])
        foreign.update(link['reminder_id'] for link in binding.get('tasks', {}).values() if link.get('reminder_id'))
        foreign.update(binding.get('history', {}))
    if any(row['id'] in foreign for row in rows):
        raise ValueError('foreign_reminder_binding')


def cancellation_sync_module():
    spec = importlib.util.spec_from_file_location('structure_cancellation_sync', Path(__file__).with_name('reminders_sync.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def verified_cancelled_ids(hub, pid, binding, config, native):
    links = {tid: link for tid, link in binding.get('tasks', {}).items() if link.get('cancellation')}
    sync = cancellation_sync_module()
    external = sync.external_retirement_module()
    retired = set(external.collect(hub, config, pid, native)) if external else set()
    if not links: return retired
    cancellation = sync.cancellation_module()
    if cancellation is None: raise ValueError('cancellation_validator_unavailable')
    rows = sync.HubProject(hub, pid).rows()
    class Reader:
        def call(self, tool, args):
            if tool not in {'hub_cancel_status', 'list_lists', 'find_reminders', 'get_reminder'}:
                raise ValueError('cancellation_status_only')
            if tool == 'hub_cancel_status' and hasattr(native, 'cancellation_status'):
                return native.cancellation_status(args)
            return native.call(tool, args)
    verified = set(retired)
    for tid, link in links.items():
        if tid not in rows: raise ValueError('missing_cancelled_task')
        row = dict(rows[tid], project_id=pid)
        if not cancellation.verify_cancelled_link(hub, row, link, binding, Reader()): raise ValueError('unverified_cancellation')
        verified.add(link['reminder_id'])
    return verified


def validate_project_list(pid, binding, snap, config, current=None, cancelled_ids=()):
    lid = binding['list_id']
    structure = config['structure']
    role = structure['list_roles'].get(lid)
    row = snap['lists'].get(lid, {})
    baseline = structure['projects'][pid]
    if (role != {'kind': 'project', 'project_id': pid} or
            sum(b['list_id'] == lid for b in config['projects'].values()) != 1 or
            row.get('name') != binding['list_name'] or 'native_group_id' not in binding or
            row.get('group_id') != binding['native_group_id'] or baseline['list_id'] != lid or
            (current is not None and current != baseline['group'])):
        raise ValueError('project_list_structure_conflict')
    known = {t['reminder_id'] for t in binding.get('tasks', {}).values() if t.get('reminder_id')} | set(binding.get('history', {}))
    known -= set(cancelled_ids)
    rows = snap['reminders']
    if set(cancelled_ids) & set(rows): raise ValueError('cancelled_reminder_reappeared')
    validate_project_ownership(pid, (row for row in rows.values() if row['list_id'] == lid), config)
    for rid in known:
        child = rows.get(rid, {})
        if child.get('list_id') != lid or child.get('parent_id') is not None:
            raise ValueError('missing_bound_child')
    retired = retired_parent_ids(config, snap)
    for row in rows.values():
        if row['id'] in retired:
            continue
        if row['list_id'] == lid:
            # Genuine nested children are opaque; only list roots participate in sync.
            if row.get('parent_id') is None and identity_owner(row.get('notes'), config) not in (None, pid):
                raise ValueError('foreign_identity')
        elif any(line == 'Hub project: ' + pid or line == 'Хаб: ' + hashlib.sha256((pid + '\0' + tid).encode()).hexdigest()[:12]
                 for tid in binding.get('tasks', {}) for line in (row.get('notes') or '').splitlines()):
            raise ValueError('incomplete_project_tree')
    return lid


def validate_tree(pid,binding,snap,config,cancelled_ids=()):
    if binding.get('layout') == 'project_list':
        return validate_project_list(pid, binding, snap, config, cancelled_ids=cancelled_ids)
    retired = retired_parent_ids(config, snap)
    rows=snap['reminders']
    if set(cancelled_ids) & set(rows): raise ValueError('cancelled_reminder_reappeared')
    parent=rows.get(binding['parent_id'])
    if parent is None:raise ValueError('missing_project_parent')
    if parent.get('parent_id'):raise ValueError('parent_is_subtask')
    lid=parent['list_id']
    if config.get('structure', {}).get('list_roles', {}).get(lid, {}).get('kind') == 'project':
        raise ValueError('exclusive_project_list')
    known={t['reminder_id'] for t in binding.get('tasks',{}).values() if t.get('reminder_id')} | set(binding.get('history',{}))
    known -= set(cancelled_ids)
    for rid in known:
        child=rows.get(rid)
        if child is None or child['list_id']!=lid or child.get('parent_id')!=parent['id']:
            raise ValueError('missing_bound_child')
    parent_owners={b['parent_id']:owner for owner,b in config['projects'].items() if b.get('parent_id')}
    all_bound=dict(parent_owners)
    for owner,b in config['projects'].items():
        all_bound.update({t['reminder_id']:owner for t in b.get('tasks',{}).values() if t.get('reminder_id')})
        all_bound.update({rid:owner for rid in b.get('history',{})})
    for row in rows.values():
        if row['id'] in retired:
            continue
        if row.get('parent_id')==parent['id']:
            if all_bound.get(row['id'],pid)!=pid or identity_owner(row.get('notes'),config) not in (None,pid):
                raise ValueError('foreign_identity')
            if row['list_id']!=lid:raise ValueError('incomplete_project_tree')
        try:
            owner=identity_owner(row.get('notes'),config,parent_owners.get(row['id']))
        except ValueError:
            container_owner=all_bound.get(row.get('parent_id')) or all_bound.get(row['id'])
            if container_owner is not None and container_owner!=pid:
                continue
            raise
        if owner==pid and row['id']!=parent['id'] and (row['list_id']!=lid or row.get('parent_id')!=parent['id']):
            raise ValueError('incomplete_project_tree')
    if identity_owner(parent.get('notes'),config,pid) not in (None,pid):raise ValueError('foreign_identity')
    return lid


def nonstructural_config(config):
    view=copy.deepcopy(config)
    for binding in view['projects'].values():
        binding.pop('list_id',None)
        binding.pop('list_name',None)
    view['structure'].pop('projects',None)
    view['structure'].pop('subgroups',None)
    return view


def validate_journal(hub, current, pending):
    """Журнал может повторить только узкую подтверждённую структурную запись."""
    try:
        before_config=pending['config']
        rows=pending['files']
        bypath={row['path']:row for row in rows}
        if len(bypath)!=len(rows):raise ValueError()
        registry=hub/'ai/project-registry.md'
        registry_text=safe_path(registry).read_text()
        cards=registry_cards(hub,registry_text)
        registered_paths=set(cards.values())
        for relative in re.findall(r'^Card: (.+)$',registry_text,re.M):
            card=safe_path(hub/relative)
            if card.parent!=hub/'ai/project-cards':raise ValueError()
            registered_paths.add(card)
        config_path=hub/'ai/reminders-sync.json'
        arch_path=hub/'ai/archiprojects.md'
        allowed_guards=registered_paths|{registry,arch_path,safe_path(standard_allowlist(current)),safe_path(current['structure']['groups_allowlist_file'])}
        guard_paths={safe_path(guard['path']) for guard in pending['guards']}
        if not guard_paths<=allowed_guards:raise ValueError()
        required_guards={registry,safe_path(standard_allowlist(current)),safe_path(current['structure']['groups_allowlist_file'])}
        if not required_guards<=guard_paths:raise ValueError()
        arch_before=bypath.get('ai/archiprojects.md',{}).get('before',safe_path(arch_path).read_text())
        groups=load_groups(arch_before)
        config_row=bypath.get('ai/reminders-sync.json')
        if config_row is None and before_config!=current:raise ValueError()
        after_config=json.loads(config_row['after']) if config_row else before_config
        if nonstructural_config(after_config)!=nonstructural_config(before_config):raise ValueError()
        old_structure=before_config['structure']
        new_structure=after_config['structure']
        if set(new_structure['projects'])!=set(old_structure['projects']) or set(new_structure['subgroups'])!=set(old_structure['subgroups']):raise ValueError()
        snap=pending['snapshot']
        for pid,binding in before_config['projects'].items():
            old=old_structure['projects'][pid]
            new=new_structure['projects'][pid]
            new_binding=after_config['projects'][pid]
            if new==old and new_binding['list_id']==binding['list_id'] and new_binding['list_name']==binding['list_name']:continue
            parent=snap['reminders'][binding['parent_id']]
            lid=parent['list_id']
            role=old_structure['list_roles'][lid]
            group=role['archiproject_id'] if role['kind']=='subgroup' else remote_group(snap['lists'][lid],old_structure,groups)
            if new!=dict(old,group=group,list_id=lid) or new_binding['list_id']!=lid or new_binding['list_name']!=snap['lists'][lid]['name']:raise ValueError()
        for gid,old in old_structure['subgroups'].items():
            new=new_structure['subgroups'][gid]
            if new==old:continue
            parent=remote_group(snap['lists'][old['list_id']],old_structure,groups)
            parent=None if parent=='none' else parent
            if new!=dict(old,parent=parent):raise ValueError()
        expected_arch=arch_before
        card_owners={path:pid for pid,path in cards.items()}
        for row in rows:
            relative=Path(row['path'])
            if relative.is_absolute() or '..' in relative.parts:raise ValueError()
            path=safe_path(hub/relative)
            if path==config_path:
                if json.loads(row['before'])!=before_config:raise ValueError()
            elif path==arch_path:
                after_groups=load_groups(row['after'])
                if set(after_groups)!=set(groups):raise ValueError()
                for gid,group in groups.items():
                    if after_groups[gid]==group:continue
                    if gid not in old_structure['subgroups'] or after_groups[gid]!=dict(group,parent=new_structure['subgroups'][gid]['parent']):raise ValueError()
                    expected_arch=replace_parent(expected_arch,gid,after_groups[gid]['parent'])
                if row['after']!=expected_arch:raise ValueError()
                subgroup_scope(hub,registry_text,groups,next(iter(old_structure['subgroups'])),{})
            elif path in card_owners:
                pid=card_owners[path]
                existing=card_group(row['before'],pid,groups)
                target=new_structure['projects'][pid]['group']
                if existing==target:raise ValueError()
                expected=replace_primary(row['before'],target)
                if row['after']!=expected:raise ValueError()
            else:raise ValueError()
    except (KeyError,TypeError,ValueError,OSError,StopIteration):
        raise ValueError('unsafe_structure_journal') from None


def replace_parent(text,gid,parent):
    pattern=r'(^## '+re.escape(gid)+r'\n)(.*?)(?=^## |\Z)'
    def replace(match):
        body=match[2]
        if re.search(r'^parent:.*$',body,re.M):
            body=re.sub(r'^parent:.*$', 'parent: '+(parent or ''), body, count=1,flags=re.M)
        else:
            body=body.replace('id: '+gid+'\n','id: '+gid+'\nparent: '+(parent or '')+'\n',1)
        return match[1]+body
    return re.sub(pattern,replace,text,flags=re.M|re.S)


def recover(journal, hub, validate_only=False):
    value=json.loads(journal.read_text())
    if value.get('version')!=1 or value.get('status') not in {'pending','complete'}:raise ValueError('invalid_structure_journal')
    if value['status']=='complete':return False
    entries=value['files']
    for guard in value['guards']:
        actual=safe_path(guard['path']).read_bytes()
        if hashlib.sha256(actual).hexdigest()!=guard['sha256']:
            raise ValueError('structure_recovery_guard_changed')
    for row in entries:
        path=safe_path(hub/row['path'])
        if path not in {hub/'ai/reminders-sync.json',hub/'ai/archiprojects.md'} and path.parent!=hub/'ai/project-cards':
            raise ValueError('unsafe_journal_target')
        if path.read_text() not in (row['before'],row['after']):raise ValueError('structure_recovery_third_state')
    if validate_only:return False
    for row in entries:
        path=safe_path(hub/row['path'])
        actual=path.read_text()
        if actual not in (row['before'],row['after']):raise ValueError('structure_recovery_third_state')
        if actual==row['before']:
            atomic_write(path,row['after'])
    value['status']='complete'
    atomic_write(journal,encoded(value))
    return True


def reconcile_structure_legacy(hub,config,apply=False,native=None):
    migrating=migration_pending(hub,config)
    if migrating:
        return dict(config=copy.deepcopy(config),items=[dict(project=pid,error='migration_recovery_required')for pid in sorted(migrating)],blocked_projects=sorted(migrating),ok=False)
    effective=copy.deepcopy(config)
    result={'config':effective,'items':[],'blocked_projects':[],'ok':True}
    structure=effective.get('structure',{})
    if not structure.get('enabled'):return result
    all_projects=list(config['projects'])
    def error(message,pid=None):
        result['ok']=False
        affected=[pid] if pid else all_projects
        result['blocked_projects']=sorted(set(result['blocked_projects'])|set(affected))
        result['items'].append({'project':pid or '*','error':str(message)})
    try:
        hub=safe_path(Path(hub).absolute())
        config_path=safe_path(hub/'ai/reminders-sync.json')
        journal_relative=Path(structure['journal_file'])
        if journal_relative.is_absolute() or '..' in journal_relative.parts or journal_relative.parent!=Path('ai') or journal_relative.name in {'reminders-sync.json','archiprojects.md','project-registry.md'}:
            raise ValueError('unsafe_journal_path')
        journal=safe_path(hub/journal_relative)
        if journal.exists() and json.loads(journal.read_text()).get('status')!='complete' and pending_structure_projects(hub,config):
            if not apply:raise ValueError('structure_recovery_required')
            pending=json.loads(journal.read_text())
            pending_config=pending['config']
            if nonstructural_config(pending_config)!=nonstructural_config(config):
                raise ValueError('structure_recovery_config_mismatch')
            config_entries=[row for row in pending['files'] if row['path']=='ai/reminders-sync.json']
            if config_entries and json.loads(config_entries[0]['before'])!=pending_config:
                raise ValueError('structure_recovery_config_mismatch')
            validate_journal(hub,config,pending)
            recover(journal,hub,validate_only=True)
            allow=json.loads(safe_path(standard_allowlist(config)).read_text())
            names=set(allow.get('names',[]) if isinstance(allow,dict) else allow)
            reader=native or StructureNative(config)
            fresh_reads()
            if snapshot(reader,pending_config['structure']['list_roles'],names,detailed_ids=retired_parent_read_ids(pending_config))!=pending['snapshot']:
                raise ValueError('structure_snapshot_changed')
            recover(journal,hub)
            effective=json.loads(config_path.read_text())
            config=copy.deepcopy(effective)
            result['config']=effective
            structure=effective['structure']
            result['items'].append({'action':'structure_recovered'})
        source=config_path.read_text()
        if json.loads(source)!=config:raise ValueError('structure_config_changed')
        registry=safe_path(hub/'ai/project-registry.md')
        arch=safe_path(hub/'ai/archiprojects.md')
        originals={config_path:source,registry:registry.read_text(),arch:arch.read_text()}
        groups=load_groups(originals[arch])
        cards=registry_cards(hub,originals[registry])
        roles=structure['list_roles']
        if set(structure['projects'])!=set(config['projects']):raise ValueError('missing_structure_baseline')
        for gid in structure['native_groups'].values():
            if gid not in groups or groups[gid]['status']!='active':raise ValueError('unknown_archiproject_group')
        allow=json.loads(safe_path(standard_allowlist(config)).read_text())
        names=set(allow.get('names',[]) if isinstance(allow,dict) else allow)
        group_allow=safe_path(structure['groups_allowlist_file'])
        originals[group_allow]=group_allow.read_text()
        allow_path=safe_path(standard_allowlist(config))
        originals[allow_path]=allow_path.read_text()
        native=native or StructureNative(config)
        first=snapshot(native,roles,names,detailed_ids=retired_parent_read_ids(config))
        after={}
        subgroup_failures=set()
        new_groups=copy.deepcopy(groups)
        for lid,role in roles.items():
            if role.get('kind') not in {'direct','subgroup','project'}:raise ValueError('unconfirmed_list_role')
            if role['kind']!='subgroup':continue
            gid=role.get('archiproject_id')
            affected=[]
            try:
                baseline=structure['subgroups'][gid]
                if gid not in groups or baseline['list_id']!=lid:raise ValueError('invalid_subgroup_binding')
                remote=remote_group(first['lists'][lid],structure,groups)
                parent=None if remote=='none' else remote
                three_way(groups[gid]['parent'],baseline['parent'],parent)
                new_groups[gid]['parent']=parent
                validate_groups(new_groups)
                if groups[gid]['parent']!=parent:
                    affected=subgroup_scope(hub,originals[registry],groups,gid,originals)
                    after[arch]=replace_parent(after.get(arch,originals[arch]),gid,parent)
                    result['items'].append({'action':'structure_subgroup_parent','archiproject':gid,'parent':parent,'affected_projects':affected})
                structure['subgroups'][gid]['parent']=parent
            except Exception as exc:
                new_groups[gid]=copy.deepcopy(groups[gid]) if gid in groups else {}
                subgroup_failures.add(gid)
                affected_active=[pid for pid in affected if pid in config['projects']]
                if not affected_active:
                    descendants={gid}
                    while True:
                        expanded=descendants|{g for g,v in groups.items() if v['parent'] in descendants}
                        if expanded==descendants:break
                        descendants=expanded
                    affected_active=[pid for pid,b in structure['projects'].items() if b['group'] in descendants]
                if not affected_active:error(exc)
                for affected_pid in affected_active:error(exc,affected_pid)
        owners={}
        for pid,binding in config['projects'].items():
            for rid in [*([binding['parent_id']] if binding.get('parent_id') else []),*[t['reminder_id'] for t in binding.get('tasks',{}).values() if t.get('reminder_id')],*binding.get('history',{})]:
                if rid in owners:raise ValueError('duplicate_reminder_binding')
                owners[rid]=pid
        for pid,binding in effective['projects'].items():
            if pid in result['blocked_projects']:continue
            try:
                if binding.get('archive'):
                    archive_module(config).verify_archived(hub, config, pid, first)
                    continue
                if pid not in cards:raise ValueError('unregistered_or_inactive_project')
                card=cards[pid]
                originals[card]=card.read_text()
                current=card_group(originals[card],pid,groups)
                baseline=structure['projects'][pid]
                if baseline['list_id']!=binding['list_id']:raise ValueError('structure_binding_baseline_mismatch')
                cancelled_ids = verified_cancelled_ids(hub, pid, binding, config, native)
                if binding.get('layout') == 'project_list':
                    validate_project_list(pid, binding, first, config, current, cancelled_ids)
                    continue
                lid=validate_tree(pid,binding,first,config,cancelled_ids)
                if cancelled_ids and (lid != binding['list_id'] or first['lists'][lid]['name'] != binding['list_name']): raise ValueError('cancellation_relocation_unsupported')
                role=roles[lid]
                if role['kind']=='subgroup':
                    remote=role['archiproject_id']
                    if remote in subgroup_failures:raise ValueError('subgroup_structure_conflict')
                else:remote=remote_group(first['lists'][lid],structure,groups)
                three_way(current,baseline['group'],remote)
                if current!=remote:
                    after[card]=replace_primary(originals[card],remote)
                if current!=remote or lid!=binding['list_id'] or first['lists'][lid]['name']!=binding['list_name'] or baseline['group']!=remote:
                    result['items'].append({'project':pid,'action':'structure_project','group':remote,'list_id':lid})
                binding.update(list_id=lid,list_name=first['lists'][lid]['name'])
                baseline.update(group=remote,list_id=lid)
            except Exception as exc:error(exc,pid)
        if effective!=config:after[config_path]=encoded(effective)
        if after and apply:
            fresh_reads()
            if snapshot(native,roles,names,detailed_ids=retired_parent_read_ids(config))!=first:raise ValueError('structure_snapshot_changed')
            for path,text in originals.items():
                if safe_path(path).read_text()!=text:raise ValueError('structure_file_changed: '+str(path))
            files=[{'path':str(path.relative_to(hub)),'before':originals[path],'after':text} for path,text in after.items()]
            guards=[{'path':str(path),'sha256':hashlib.sha256(text.encode()).hexdigest()} for path,text in originals.items() if path not in after]
            transaction={'version':1,'status':'pending','files':files,'guards':guards,'snapshot':first,'config':copy.deepcopy(config)}
            validate_journal(hub,config,transaction)
            atomic_write(journal,encoded(transaction))
            recover(journal,hub)
    except Exception as exc:
        error(exc)
        result['config']=copy.deepcopy(config)
    return result


def reconcile_structure(hub,config,apply=False,native=None):
    migrating = migration_pending(hub, config)
    if migrating:
        return dict(config=copy.deepcopy(config), items=[dict(project=pid, error='migration_recovery_required') for pid in sorted(migrating)], blocked_projects=sorted(migrating), ok=False)
    structure=config.get('structure',{})
    if not structure.get('bidirectional'):
        if structure.get('outgoing_intent_sha256') and structure.get('outgoing_intent_sha256')!=structure.get('outgoing_completed_sha256'):
            return dict(config=copy.deepcopy(config),items=[dict(project='*',error='structure_recovery_required',direction='conflict')],blocked_projects=sorted(config['projects']),ok=False)
        return reconcile_structure_legacy(hub,config,apply,native)
    path=safe_path(Path(__file__).absolute().with_name('reminders_bidirectional.py'))
    spec=importlib.util.spec_from_file_location('reminders_bidirectional',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Explicit facade keeps the legacy implementation and its recovery unchanged.
    facade=type('StructureFacade',(),{name:staticmethod(value) if callable(value) else value for name,value in globals().items() if not name.startswith('__')})
    return module.reconcile(facade,hub,config,apply,native)
