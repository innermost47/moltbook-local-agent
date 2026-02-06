<?php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-API-Key');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once "utils.php";
require_once 'config.php';

$api_key = $_SERVER['HTTP_X_API_KEY'] ?? '';

if ($api_key !== MOLTBOOK_LOCAL_AGENT_BLOG_API_KEY) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Invalid API key']);
    exit;
}

try {
    $keys_db = new PDO('sqlite:' . COMMENT_KEYS_DB_PATH);
    $keys_db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $stmt = $keys_db->query("
            SELECT request_id, agent_name, agent_description, contact_email, created_at
            FROM key_requests
            WHERE status = 'pending'
            ORDER BY created_at ASC
        ");

        $pending = $stmt->fetchAll(PDO::FETCH_ASSOC);

        http_response_code(200);
        echo json_encode([
            'success' => true,
            'count' => count($pending),
            'requests' => $pending
        ]);
        exit;
    }

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $input = file_get_contents('php://input');
        $data = json_decode($input, true);

        if (!$data) {
            http_response_code(400);
            echo json_encode(['success' => false, 'error' => 'Invalid JSON']);
            exit;
        }

        $request_id = $data['request_id'] ?? '';
        $action = $data['action'] ?? '';

        if (empty($request_id) || !in_array($action, ['approve', 'reject'])) {
            http_response_code(400);
            echo json_encode(['success' => false, 'error' => 'Invalid parameters']);
            exit;
        }

        $stmt = $keys_db->prepare("
            SELECT agent_name, status FROM key_requests WHERE request_id = ?
        ");
        $stmt->execute([$request_id]);
        $request = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$request) {
            http_response_code(404);
            echo json_encode(['success' => false, 'error' => 'Request not found']);
            exit;
        }

        if ($request['status'] !== 'pending') {
            http_response_code(400);
            echo json_encode(['success' => false, 'error' => 'Request already processed']);
            exit;
        }

        if ($action === 'approve') {
            $api_key = bin2hex(random_bytes(32));

            $keys_db->beginTransaction();

            $stmt = $keys_db->prepare("
                UPDATE key_requests 
                SET status = 'approved', api_key = ?, approved_at = datetime('now')
                WHERE request_id = ?
            ");
            $stmt->execute([$api_key, $request_id]);

            $stmt = $keys_db->prepare("
                INSERT INTO api_keys (api_key, agent_name, status, created_at)
                VALUES (?, ?, 'active', datetime('now'))
            ");
            $stmt->execute([$api_key, $request['agent_name']]);

            $keys_db->commit();

            write_logs("Auto-approved comment key for: {$request['agent_name']}");

            http_response_code(200);
            echo json_encode([
                'success' => true,
                'action' => 'approved',
                'agent_name' => $request['agent_name'],
                'api_key' => $api_key
            ]);
        } else {
            $stmt = $keys_db->prepare("
                UPDATE key_requests 
                SET status = 'rejected'
                WHERE request_id = ?
            ");
            $stmt->execute([$request_id]);

            write_logs("Auto-rejected comment key for: {$request['agent_name']}");

            http_response_code(200);
            echo json_encode([
                'success' => true,
                'action' => 'rejected',
                'agent_name' => $request['agent_name']
            ]);
        }
    }
} catch (PDOException $e) {
    write_logs("Database error in auto_approve_keys.php: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Database error']);
}
