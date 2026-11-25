<?php
/*
 * trash.php — list, restore or empty the device-local trash of the shared folder.
 *
 * The store lives outside the synced folder, under the state directory by
 * default (ADR-0056), so every action runs through ``hsync trash`` with the same
 * HSYNC_STATE_DIR/HSYNC_TRASH_DIR the daemon uses. Nothing here touches the
 * share, the state database or the daemon: a restore is a plain local write that
 * the running sync propagates at its next cycle, so no stop/start is needed.
 */

require __DIR__ . '/env_lib.php';

hsync_require_post();

$folder = hsync_data_path();
if (!is_dir($folder)) {
    hsync_reply(['ok' => false, 'error' => 'missing_folder'], 400);
}

$action = (string)($_POST['action'] ?? 'list');

switch ($action) {
    case 'list':
        [$ok, $out, $err] = hsync_run(['trash', 'list', '--folder', $folder, '--json']);
        if (!$ok) {
            hsync_reply(['ok' => false, 'error' => 'list_failed', 'detail' => trim($err)], 502);
        }
        $entries = json_decode($out, true);
        if (!is_array($entries)) {
            // A truncated listing must be reported, never rendered as "no
            // deleted files": that would look like the trash is empty.
            hsync_reply(['ok' => false, 'error' => 'list_failed', 'detail' => 'unparsable listing'], 502);
        }
        // One stats call answers "X of Y": the size budget is shared by every
        // share, so the figures are the store's, not this folder's.
        [$statsOk, $statsOut] = hsync_run(['trash', 'stats', '--json']);
        $stats = $statsOk ? json_decode($statsOut, true) : null;
        hsync_reply([
            'ok' => true,
            'entries' => is_array($entries) ? $entries : [],
            'trash_dir' => hsync_trash_root(),
            // A store on another volume than the share copies the bytes on both
            // moves; the UI states it instead of implying an instant rename.
            'same_volume' => hsync_same_volume(hsync_trash_root(), $folder),
            'stats' => is_array($stats) ? $stats : null,
        ]);
        break;

    case 'restore':
        // Bucket-relative path; the client re-validates it against the store's
        // own grammar (no absolute path, no traversal, no NUL).
        $relpath = (string)($_POST['path'] ?? '');
        if ($relpath === ''
            || preg_match('/[\x00-\x1F\x7F]/', $relpath)
            || $relpath[0] === '/'
            || str_contains('/' . $relpath . '/', '/../')) {
            hsync_reply(['ok' => false, 'error' => 'bad_path'], 400);
        }
        // The direction decides whether the restore is allowed at all: a
        // download-only folder would delete the file again, so the client
        // refuses it there instead of creating a loop.
        $env = hsync_parse_env(HSYNC_ENV_FILE);
        $direction = (string)($env['HSYNC_SYNC_DIRECTION'] ?? 'bidirectional');
        if (!in_array($direction, ['bidirectional', 'upload-only', 'download-only'], true)) {
            $direction = 'bidirectional';
        }
        [$ok, $out, $err] = hsync_run([
            'trash', 'restore', $relpath, '--folder', $folder, '--direction', $direction,
        ]);
        if (!$ok) {
            hsync_reply(['ok' => false, 'error' => 'restore_failed', 'detail' => trim($err)], 502);
        }
        hsync_reply(['ok' => true, 'message' => trim($out)]);
        break;

    case 'empty':
        [$ok, $out, $err] = hsync_run(['trash', 'empty', '--folder', $folder, '--yes']);
        if (!$ok) {
            hsync_reply(['ok' => false, 'error' => 'empty_failed', 'detail' => trim($err)], 502);
        }
        hsync_reply(['ok' => true, 'message' => trim($out)]);
        break;

    default:
        hsync_reply(['ok' => false, 'error' => 'bad_action'], 400);
}
