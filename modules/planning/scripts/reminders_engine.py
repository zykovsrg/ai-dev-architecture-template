#!/usr/bin/env python3
"""Полный контекст чтения → штатный расчёт и запись → свежая полная проверка.

Контекст никогда не переживает fresh_reads или попытку нативной записи.
Старые журналы восстанавливаются прежним исполнителем до нового планирования.
"""
import contextlib
import copy
import datetime
import json
import hashlib
from pathlib import Path

class SnapshotProtocolError(ValueError):
    pass


READS = {'list_lists', 'find_reminders', 'get_reminder', 'hub_cancel_status', 'hub_cancel_capabilities'}


class ContextNative:
    def __init__(self, native, observation, reads):
        self.native = native
        self.observation = copy.deepcopy(observation)
        self.reads = reads
        self.epoch = reads.generation() if reads else 0
        self.valid = True
        self.rows = {r['id']: r for rows in self.observation['lists'].values() for r in rows}

    def current(self):
        if self.valid:
            try:
                for filename, expected in self.observation.get('_scope_files', {}).items():
                    path = Path(filename)
                    if any(p.is_symlink() for p in (path, *path.parents)) or path.read_bytes() != expected:
                        self.invalidate()
                        break
            except OSError:
                self.invalidate()
        return self.valid and (not self.reads or self.epoch == self.reads.generation())

    def invalidate(self):
        self.valid = False
        if self.reads:
            self.reads.refresh()

    def validated_observation(self):
        """Полный снимок для прежних валидаторов, только до записи или новой границы чтения."""
        if self.observation.get('complete') is not True or not self.current():
            return None
        return copy.deepcopy(self.observation)

    def call(self, tool, args):
        if tool not in READS:
            self.invalidate()  # В том числе неизвестный результат и исключение записи.
            return self.native.call(tool, args)
        if not self.current():
            return self.native.call(tool, args)
        if tool == 'list_lists' and args == {}:
            return copy.deepcopy(self.observation['metadata'])
        if tool == 'find_reminders' and args.get('include_completed') is True and args.get('limit') == 500 and set(args) <= {'list', 'include_completed', 'limit', 'detail'}:
            lid = args['list']
            if lid not in self.observation['lists']:
                error = next((r['error'] for r in self.observation.get('errors', []) if r.get('list_id') == lid), 'engine_unknown_list')
                raise ValueError(error)
            rows = copy.deepcopy(self.observation['lists'][lid])
            return dict(reminders=rows, count=len(rows), has_more=False, **({'detail': True} if args.get('detail') else {}))
        if tool == 'get_reminder' and set(args) == {'id'}:
            if args['id'] not in self.rows:
                raise ValueError('engine_missing_binding')
            return copy.deepcopy(self.rows[args['id']])
        return self.native.call(tool, args)

    def get(self, rid, list_id, *parents):
        if not self.current():
            return self.native.get(rid, list_id, *parents)
        value = self.call('get_reminder', {'id': rid})
        if value.get('list_id') != list_id or parents and value.get('parent_id') != parents[0]:
            raise ValueError('engine_binding_mismatch')
        return value

    def children(self, binding):
        if not self.current():
            return self.native.children(binding)
        value = self.call('find_reminders', dict(list=binding['list_id'], include_completed=True, limit=500))
        return [r for r in value['reminders'] if r.get('parent_id') == binding.get('parent_id')]

    def update(self, row, changes):
        self.invalidate()
        return self.native.update(row, changes)

    def cancellation_status(self, args):
        target = getattr(self.native, 'cancellation_status', None)
        return target(args) if target else self.native.call('hub_cancel_status', args)


def capture(m, hub, config, native):
    """Полнота и область проверяются штатно; подробности читаются одним проходом."""
    captured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    scope_paths = {str(m.safe_path(config['allowlist_file'])), str(m.safe_path(m.standard_allowlist(config)))}
    scope_paths.update(str(m.safe_path(config['structure'][key])) for key in
                       ('groups_allowlist_file', 'group_ids_allowlist_file')
                       if config.get('structure', {}).get(key))
    scope_files = {path: Path(path).read_bytes() for path in scope_paths}
    reads = m.reads_module()
    if reads:
        reads.refresh()
    with contextlib.nullcontext():
        external = m.external_retirement_module()
        raw_metadata = []
        class ObservedNative:
            def call(self, tool, args):
                value = native.call(tool, args)
                if tool == 'list_lists':
                    raw_metadata.append(copy.deepcopy(value))
                return value
        observation = external.observe(Path(hub), config, ObservedNative(), partial=True)
        # Нативный краткий формат может не повторять UUID списка в каждой строке.
        for lid, rows in observation['lists'].items():
            for row in rows:
                row.setdefault('list_id', lid)
        observation['captured_at'] = captured_at
        observation['_scope_files'] = scope_files
        class CaptureNative:
            def call(self, tool, args):
                if tool == 'list_lists':
                    value = copy.deepcopy(observation['metadata'])
                    value['lists'] = [r for r in value['lists'] if r['id'] in observation['lists']]
                    if raw_metadata and raw_metadata[0].get('detailed_reminder_snapshot') is True:
                        value['detailed_reminder_snapshot'] = True
                    return value
                if tool == 'find_reminders' and not args.get('detail'):
                    rows = copy.deepcopy(observation['lists'][args['list']])
                    return dict(reminders=rows, count=len(rows), has_more=False)
                if tool == 'get_reminder':
                    summary = next(r for rows in observation['lists'].values() for r in rows if r['id'] == args['id'])
                    return native.get(args['id'], summary['list_id'])
                return native.call(tool, args)
        structural = m.structure_module()
        roles = config.get('structure', {}).get('list_roles')
        if roles is None:
            roles = {r['id']: {} for r in observation['metadata']['lists']}
        # Неполные списки не превращаем в пустые; детали проверяем только для прочитанных.
        roles = {lid: role for lid, role in roles.items() if lid in observation['lists']}
        try:
            snap = structural.snapshot(CaptureNative(), roles, set(observation['scope']['names']), detailed=True, include_groups=True)
        except (ValueError, KeyError, TypeError, RuntimeError) as error:
            if raw_metadata and raw_metadata[0].get('detailed_reminder_snapshot') is True:
                raise SnapshotProtocolError(str(error)) from error
            raise
        # В том числе старый протокол get: детали не могут опровергать краткий снимок.
        for rows in observation['lists'].values():
            for row in rows:
                detail = snap['reminders'][row['id']]
                if any(detail.get(k) != row.get(k) for k in ('id', 'version', 'title', 'parent_id', 'completed', 'due')) or detail.get('list_id') != row.get('list_id', detail.get('list_id')):
                    raise ValueError('engine_snapshot_changed')
        with reads.direct_reads() if reads else contextlib.nullcontext():
            after = external.metadata(native, observation['scope']['names'])
        if any(m.safe_path(path).read_bytes() != expected for path, expected in scope_files.items()):
            raise ValueError('engine_permission_scope_changed')
        if after != observation['metadata']:
            raise ValueError('engine_metadata_changed')
        if raw_metadata and raw_metadata[0].get('detailed_reminder_snapshot') is True:
            observation['metadata']['detailed_reminder_snapshot'] = True
        listing_names = {r['id']: r['name'] for r in observation['metadata']['lists']}
        observation['lists'] = {lid: [dict(copy.deepcopy(r), list=listing_names[lid]) for r in snap['reminders'].values() if r['list_id'] == lid] for lid in roles}
        return observation


def export_snapshot(observation):
    return dict(complete=bool(observation.get('complete')),
                metadata=copy.deepcopy(observation.get('metadata')),
                reminders=[copy.deepcopy(r) for rows in observation.get('lists', {}).values() for r in rows],
                captured_at=observation.get('captured_at', datetime.datetime.now(datetime.timezone.utc).isoformat()),
                scope=copy.deepcopy(observation.get('scope')),
                limitations=[] if observation.get('complete') else ['incomplete_permitted_scope'])


def pending(m, hub, config):
    """Не перепланируем поверх частично исполненных исторических операций."""
    if (m.migration_pending(hub, config) or m.task_reassignment_pending(hub, config)
            or m.structure_module().pending_structure_projects(hub, config)
            or m.gateway_module().pending_projects(hub)):
        return True
    external = m.external_retirement_module()
    cancellation = m.cancellation_module()
    if external and external.pending_projects(hub, config) or cancellation and cancellation.pending_projects(hub, config):
        return True
    return any(link.get('pending_create') or link.get('pending_import') or link.get('pending_notes')
               for binding in config['projects'].values() for link in binding.get('tasks', {}).values())


def failed_snapshot(error):
    return dict(complete=False, metadata=None, reminders=[], captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope=None, limitations=['final_snapshot_unavailable: ' + str(error)])


def finish(m, hub, config, native, result, project, reconcile, return_snapshot):
    try:
        current = m.load_config(hub)
        config.clear(); config.update(current)
        if hasattr(native, 'config'):
            native.config = config
        observation = capture(m, hub, config, native)
        if not observation.get('complete'):
            raise ValueError('incomplete_final_scope')
        final = ContextNative(native, observation, m.reads_module())
        # Та же полная логика вычисляет только оставшиеся расхождения, без записи.
        check = m._legacy_sync(hub, copy.deepcopy(config), False, project, final,
                               final if reconcile and config.get('structure', {}).get('enabled') else None, reconcile)
        actionable = {'sync', 'import', 'publish', 'resume_import', 'external_retirement'}
        if not check.get('ok') or check.get('stop') or any(r.get('action') in actionable or r.get('direction') in {'incoming','outgoing'} for r in check.get('items', [])):
            result['ok'] = False
            result.setdefault('items', []).append(dict(project='*', error='engine_final_verification_failed', details=check.get('items', [])))
        if return_snapshot:
            result['final_snapshot'] = export_snapshot(observation)
    except Exception as error:
        result['ok'] = False
        result.setdefault('items', []).append(dict(project='*', error='engine_final_read_failed: ' + str(error)))
        if return_snapshot:
            result['final_snapshot'] = failed_snapshot(error)
    return result


class LocalInputs:
    """Точные суммы локальных входов; изменения и новые квитанции отменяют no-op."""
    def __init__(self, m, hub, config):
        self.m, self.hub = m, Path(hub)
        self.paths = {self.hub / 'ai' / name for name in
                      ('reminders-sync.json', 'project-registry.md', 'archiprojects.md')}
        self.paths.update(Path(root) / 'ai' / name for root in m.task_projects(hub, config).values()
                          for name in m.NAMES.values())
        journal = config.get('structure', {}).get('journal_file')
        if journal:
            relative = Path(journal)
            if relative.is_absolute() or '..' in relative.parts or relative.parent != Path('ai'):
                raise ValueError('unsafe_engine_journal')
            self.paths.add(self.hub / relative)
        self.before = self.fingerprint()

    def fingerprint(self):
        paths = set(self.paths)
        cards = self.hub / 'ai/project-cards'
        if cards.exists():
            self.m.safe_path(cards)
            paths.update(cards.glob('*.md'))
        for root in (self.hub / 'ai').glob('reminders-*'):
            self.m.safe_path(root)
            if root.is_dir():
                # Протоколы синхронизации хранят документы только на двух уровнях.
                paths.update(root.glob('*.json'))
                for directory in root.iterdir():
                    self.m.safe_path(directory)
                    if directory.is_dir():
                        paths.update(directory.glob('*.json'))
            elif root.suffix == '.json':
                paths.add(root)
        return {str(path): hashlib.sha256(self.m.safe_path(path).read_bytes()).digest()
                if path.exists() else None for path in paths}

    def unchanged(self):
        return self.fingerprint() == self.before


def no_changes(result):
    benign = {None, 'none', 'cancellation_verified', 'recurrence_history_ignored', 'archive_verified'}
    return bool(result.get('ok') and not result.get('stop') and result.get('complete', True)
                and all(item.get('action') in benign and item.get('direction') not in {'incoming','outgoing'}
                        for item in result.get('items', [])))


def run(m, hub, config, apply=False, project=None, native=None, structure_native=None, reconcile=True, return_snapshot=False):
    # Старый режим и явно разные исполнители сохраняют прежние полномочия.
    if not m.authority_enabled(config) or structure_native is not None:
        result = m._legacy_sync(hub, config, apply, project, native, structure_native, reconcile)
        return finish(m, hub, config, native or m.Native(config), result, project, reconcile, True) if return_snapshot else result
    authority = m.authority_module()
    with authority.locked(hub):
        authority.validate_policy(hub, config)
        base = native or m.Native(config)
        if pending(m, hub, config):
            result = m._legacy_sync(hub, config, apply, project, base, None, reconcile)
            return finish(m, hub, config, base, result, project, reconcile, True) if return_snapshot else result
        try:
            local_inputs = LocalInputs(m, hub, config)
            observation = capture(m, hub, config, base)
        except Exception as error:
            # После непроверенного снимка никакой другой путь записи не запускается.
            result = dict(applied=False, ok=False, complete=False,
                          items=[dict(project='*', error='engine_snapshot_read_failed: ' + str(error))])
            if return_snapshot:
                result['final_snapshot'] = failed_snapshot(error)
            return result
        context = ContextNative(base, observation, m.reads_module())
        structural = None
        if reconcile and config.get('structure', {}).get('enabled'):
            # Сохраняем узкий набор команд структурного исполнителя.
            structural = ContextNative(m.structure_module().StructureNative(config) if native is None else base, observation, m.reads_module())
        prepared = authority.prepare_pull(m, hub, config, apply, project, context)
        if prepared['stop']:
            result = dict(applied=False, ok=True, items=prepared['items'], stop=True)
        else:
            if config is not prepared['config']:
                config.clear(); config.update(prepared['config'])
            result = m._sync(hub, config, apply, project, context, structural, reconcile,
                             prepared['items'], prepared)
        # Просмотр возвращает запланированные изменения, а не проверяет их применение.
        if not apply:
            if return_snapshot:
                result['final_snapshot'] = export_snapshot(observation)
            return result
        if no_changes(result) and context.current() and local_inputs.unchanged():
            if return_snapshot:
                result['final_snapshot'] = export_snapshot(observation)
            return result
        return finish(m, hub, config, base, result, project, reconcile, return_snapshot)
