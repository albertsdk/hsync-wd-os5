<?php
/*
 * service.php — start / stop / restart / status of the hsync daemon.
 *
 * Replaces service.php (see config_get.php for the rationale).
 *
 * Query: ?action=start|stop|restart|status
 * Returns: {"ok":true,"action":"...","running":true|false}
 */

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

require __DIR__ . '/env_lib.php';

/**
 * Run a lifecycle script.  Uses shell_exec when available, falls back to
 * proc_open/popen, so the page degrades gracefully on hardened php.ini.
 */
function runScript(string $script, bool $background): void {
    $cmd = escapeshellcmd($script) . ' ' . escapeshellarg(HSYNC_PKG_DIR) . ' >/dev/null 2>&1';
    if ($background) $cmd .= ' &';
    if (function_exists('shell_exec')) {
        @shell_exec($cmd);
    } elseif (function_exists('proc_open')) {
        $p = @proc_open(['/bin/sh', '-c', $cmd], [], $pipes);
        if (is_resource($p)) proc_close($p);
    } elseif (function_exists('popen')) {
        $h = @popen($cmd, 'r');
        if ($h) pclose($h);
    }
}

// Sanitize action: only lowercase letters allowed.
$action = preg_replace('/[^a-z]/', '', $_GET['action'] ?? '');

switch ($action) {
    case 'start':
        if (!hsync_service_running()) runScript(HSYNC_PKG_DIR . '/start.sh', true);
        break;

    case 'stop':
        if (hsync_service_running()) runScript(HSYNC_PKG_DIR . '/stop.sh', false);
        break;

    case 'restart':
        runScript(HSYNC_PKG_DIR . '/stop.sh',  false);
        runScript(HSYNC_PKG_DIR . '/start.sh', true);
        break;

    case 'status':
        // No action needed; fall through to the JSON reply below.
        break;

    default:
        http_response_code(400);
        echo '{"ok":false,"error":"invalid_action"}';
        exit;
}

echo json_encode(['ok' => true, 'action' => $action, 'running' => hsync_service_running()]);
