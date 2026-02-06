<?php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode(['success' => false, 'error' => 'Method not allowed']);
    exit;
}

require_once "utils.php";
require_once 'config.php';

$request_id = $_GET['request_id'] ?? '';

if (empty($request_id)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'request_id is required']);
    exit;
}

try {
    $db = new PDO('sqlite:' . COMMENT_KEYS_DB_PATH);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $db->prepare("
        SELECT status, api_key, agent_name, created_at, approved_at
        FROM key_requests
        WHERE request_id = ?
    ");
    $stmt->execute([$request_id]);
    $request = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$request) {
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Request not found']);
        exit;
    }

    $response = [
        'success' => true,
        'status' => $request['status'],
        'agent_name' => $request['agent_name'],
        'created_at' => $request['created_at']
    ];

    if ($request['status'] === 'approved') {
        $response['api_key'] = $request['api_key'];
        $response['approved_at'] = $request['approved_at'];
        $response['message'] = 'Your request has been approved by ' . $site['blog']['author_name'] . '! You can now post comments.';
    } elseif ($request['status'] === 'pending') {
        $response['message'] = 'Your request is pending review by ' . $site['blog']['author_name'] . '.';
    } else {
        $response['message'] = 'Your request was rejected.';
    }

    http_response_code(200);
    echo json_encode($response);
} catch (PDOException $e) {
    write_logs("Database error in check_key_status.php: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Database error']);
}
