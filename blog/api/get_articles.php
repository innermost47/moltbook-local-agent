<?php

header('Content-Type: application/json');

require_once "utils.php";
require_once 'config.php';

$api_key = $_SERVER['HTTP_X_API_KEY'] ?? '';
if ($api_key !== MOLTBOOK_LOCAL_AGENT_BLOG_API_KEY) {
    write_logs("UNAUTHORIZED: Key mismatch.", $log_file);
    http_response_code(401);
    exit(json_encode(['success' => false, 'error' => 'Invalid API Key']));
}

try {
    $db = new PDO('sqlite:' . DB_PATH);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $db->prepare("SELECT title FROM articles WHERE status = 'published' ORDER BY created_at DESC LIMIT 10");
    $stmt->execute();
    $articles = $stmt->fetchAll(PDO::FETCH_ASSOC);

    write_logs("SUCCESS: Fetched " . count($articles) . " articles using DB_PATH: " . DB_PATH, $log_file);

    echo json_encode([
        'success' => true,
        'count' => count($articles),
        'articles' => $articles
    ]);
} catch (Exception $e) {
    write_logs("SQL ERROR: " . $e->getMessage(), $log_file);
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
