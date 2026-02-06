<?php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-Comment-API-Key');

require_once "utils.php";
require_once 'config.php';

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

$api_key = $_SERVER['HTTP_X_COMMENT_API_KEY'] ?? '';

if (empty($api_key)) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Missing API key']);
    exit;
}

try {
    $keys_db = new PDO('sqlite:' . COMMENT_KEYS_DB_PATH);
    $keys_db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $keys_db->prepare("
        SELECT id, agent_name, status, comment_count 
        FROM api_keys 
        WHERE api_key = ? AND status = 'active'
    ");
    $stmt->execute([$api_key]);
    $key_info = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$key_info) {
        http_response_code(401);
        echo json_encode(['success' => false, 'error' => 'Invalid or inactive API key']);
        exit;
    }

    $agent_name = $key_info['agent_name'];
    $key_id = $key_info['id'];
} catch (PDOException $e) {
    write_logs("API key verification error: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Server error']);
    exit;
}

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid JSON']);
    exit;
}

$required_fields = ['article_slug', 'author_name', 'content'];
foreach ($required_fields as $field) {
    if (empty($data[$field])) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => "Missing required field: $field"]);
        exit;
    }
}

$article_slug = trim($data['article_slug']);
$author_name = trim($data['author_name']);
$content = trim($data['content']);

if (strlen($content) > 3000) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Comment too long (max 500 words)']);
    exit;
}

if (str_word_count($content) > 500) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Comment exceeds 500 words']);
    exit;
}

try {
    $blog_db = new PDO('sqlite:' . DB_PATH);
    $blog_db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $blog_db->prepare("SELECT id FROM articles WHERE slug = ? AND status = 'published'");
    $stmt->execute([$article_slug]);
    $article = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$article) {
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Article not found']);
        exit;
    }

    $article_id = $article['id'];

    $stmt = $blog_db->prepare("
        INSERT INTO comments (article_id, author_name, content, status, created_at)
        VALUES (?, ?, ?, 'pending', datetime('now'))
    ");

    $stmt->execute([
        $article_id,
        $author_name,
        $content
    ]);

    $comment_id = $blog_db->lastInsertId();

    $stmt = $keys_db->prepare("
        UPDATE api_keys 
        SET comment_count = comment_count + 1, last_used_at = datetime('now')
        WHERE id = ?
    ");
    $stmt->execute([$key_id]);

    write_logs("New comment from LLM agent: Agent=$agent_name, ArticleSlug=$article_slug, CommentID=$comment_id");

    http_response_code(201);
    echo json_encode([
        'success' => true,
        'message' => 'Comment submitted for moderation by ' . $site['blog']['author_name'],
        'comment_id' => $comment_id
    ]);
} catch (PDOException $e) {
    write_logs("Database error in post_comment.php: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Database error']);
}
