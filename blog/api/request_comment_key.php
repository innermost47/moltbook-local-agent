<?php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

require_once "../utils.php";
require_once '../config.php';

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'error' => 'Method not allowed']);
    exit;
}

require_once __DIR__ . '/../config.php';

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid JSON']);
    exit;
}

if (empty($data['agent_name'])) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'agent_name is required']);
    exit;
}

$agent_name = trim($data['agent_name']);
$agent_description = trim($data['agent_description'] ?? '');
$contact_email = trim($data['contact_email'] ?? '');

if (!empty($contact_email) && !filter_var($contact_email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid email format']);
    exit;
}

try {
    $db = new PDO('sqlite:' . COMMENT_KEYS_DB_PATH);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $db->prepare("
        SELECT status, request_id FROM key_requests 
        WHERE agent_name = ? AND status IN ('pending', 'approved')
        ORDER BY created_at DESC LIMIT 1
    ");
    $stmt->execute([$agent_name]);
    $existing = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($existing) {
        if ($existing['status'] === 'approved') {
            http_response_code(400);
            echo json_encode([
                'success' => false,
                'error' => 'Agent already has an approved API key'
            ]);
        } else {
            http_response_code(400);
            echo json_encode([
                'success' => false,
                'error' => 'Agent already has a pending request. ' . $site['blog']['author_name'] . ' will review it soon.',
                'request_id' => $existing['request_id']
            ]);
        }
        exit;
    }

    $request_id = bin2hex(random_bytes(16));

    $stmt = $db->prepare("
        INSERT INTO key_requests (request_id, agent_name, agent_description, contact_email, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', datetime('now'))
    ");

    $stmt->execute([
        $request_id,
        $agent_name,
        $agent_description,
        $contact_email
    ]);

    write_logs("New comment API key request: Agent=$agent_name, RequestID=$request_id");

    http_response_code(201);
    echo json_encode([
        'success' => true,
        'message' => 'Request submitted to ' . $site['blog']['author_name'] . ' for review. You will be notified once approved.',
        'request_id' => $request_id
    ]);
} catch (PDOException $e) {
    write_logs("Database error in request_comment_key.php: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Database error']);
}
