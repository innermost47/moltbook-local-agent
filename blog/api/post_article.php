<?php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-API-Key');

require_once "../utils.php";
require_once '../config.php';

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    write_logs("Rejected: Method not allowed (" . $_SERVER['REQUEST_METHOD'] . ")");
    http_response_code(405);
    echo json_encode(['success' => false, 'error' => 'Method not allowed']);
    exit;
}

$config_file = __DIR__ . '/../config.php';
if (!file_exists($config_file)) {
    write_logs("CRITICAL: config.php missing");
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Server configuration missing']);
    exit;
}

require_once $config_file;

$api_key = $_SERVER['HTTP_X_API_KEY'] ?? '';
if ($api_key !== MOLTBOOK_LOCAL_AGENT_BLOG_API_KEY) {
    write_logs("Rejected: Invalid API Key from " . $_SERVER['REMOTE_ADDR']);
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Invalid API key']);
    exit;
}

$input = file_get_contents('php://input');
write_logs("Received payload size: " . strlen($input) . " bytes");

$data = json_decode($input, true);

if (!$data) {
    write_logs("JSON Decode Error: " . json_last_error_msg());
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid JSON: ' . json_last_error_msg()]);
    exit;
}

$required_fields = ['title', 'excerpt', 'content', 'image_data'];
foreach ($required_fields as $field) {
    if (empty($data[$field])) {
        write_logs("Validation Error: Missing $field");
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => "Missing required field: $field"]);
        exit;
    }
}

$title = trim($data['title']);
$excerpt = trim($data['excerpt']);
$content = $data['content'];
$image_data = trim($data['image_data']);

if (strlen($title) > 200) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Title too long (max 200 chars)']);
    exit;
}

if (strlen($excerpt) > 500) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Excerpt too long (max 500 chars)']);
    exit;
}

if (strlen($content) > 50000) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Content too long (max 50k chars)']);
    exit;
}

if (!preg_match('/^data:image\/(png|jpeg|jpg|webp);base64,/', $image_data)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid image data format (must be base64 with data URI)']);
    exit;
}

$slug = generate_slug($title);

try {
    $db = new PDO('sqlite:' . DB_PATH);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $db->prepare("SELECT COUNT(*) FROM articles WHERE slug = ?");
    $stmt->execute([$slug]);
    $count = $stmt->fetchColumn();

    if ($count > 0) {
        $slug .= '-' . time();
    }

    write_logs("Inserting article: $slug");

    $stmt = $db->prepare("
        INSERT INTO articles (title, excerpt, content, image_data, slug, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'published', datetime('now'), datetime('now'))
    ");

    $stmt->execute([
        $title,
        $excerpt,
        $content,
        $image_data,
        $slug
    ]);

    $article_id = $db->lastInsertId();

    write_logs("SUCCESS: Article ID $article_id published.");

    $article_url = MOLTBOOK_LOCAL_AGENT_BLOG_BASE_URL . '/article.php?slug=' . urlencode($slug);

    write_logs("New article created by " . $site['blog']['author_name'] . ": ID=$article_id, Slug=$slug, Title=$title");

    http_response_code(201);
    echo json_encode([
        'success' => true,
        'message' => 'Article published successfully',
        'article_id' => $article_id,
        'slug' => $slug,
        'url' => $article_url
    ]);
} catch (PDOException $e) {
    write_logs("DATABASE ERROR: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Database error']);
    exit;
} catch (Exception $e) {
    write_logs("GENERAL ERROR: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Unexpected server error']);
}
