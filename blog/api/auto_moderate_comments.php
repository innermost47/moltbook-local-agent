<?php

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-API-Key');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once "../utils.php";
require_once '../config.php';

$api_key = $_SERVER['HTTP_X_API_KEY'] ?? '';

if ($api_key !== MOLTBOOK_LOCAL_AGENT_BLOG_API_KEY) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Invalid API key']);
    exit;
}

try {
    $blog_db = new PDO('sqlite:' . DB_PATH);
    $blog_db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $article_id = $_GET['article_id'] ?? null;
        $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 100;

        $query = "
            SELECT 
                c.id, c.article_id, c.author_name, c.content, c.created_at,
                a.title as article_title, a.slug as article_slug
            FROM comments c
            JOIN articles a ON c.article_id = a.id
            WHERE c.status = 'pending'
        ";

        if ($article_id) {
            $query .= " AND c.article_id = :article_id";
        }

        $query .= " ORDER BY c.created_at ASC LIMIT :limit";

        $stmt = $blog_db->prepare($query);

        if ($article_id) {
            $stmt->bindValue(':article_id', $article_id, PDO::PARAM_INT);
        }
        $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);

        $stmt->execute();
        $pending = $stmt->fetchAll(PDO::FETCH_ASSOC);

        echo json_encode([
            'success' => true,
            'count' => count($pending),
            'comments' => $pending
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

        $comment_id = $data['comment_id'] ?? '';
        $action = $data['action'] ?? '';

        if (empty($comment_id) || !in_array($action, ['approve', 'reject'])) {
            http_response_code(400);
            echo json_encode(['success' => false, 'error' => 'Invalid parameters']);
            exit;
        }

        $stmt = $blog_db->prepare("
            SELECT 
                c.author_name,
                c.status,
                a.title as article_title
            FROM comments c
            JOIN articles a ON c.article_id = a.id
            WHERE c.id = ?
        ");
        $stmt->execute([$comment_id]);
        $comment = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$comment) {
            http_response_code(404);
            echo json_encode(['success' => false, 'error' => 'Comment not found']);
            exit;
        }

        if ($comment['status'] !== 'pending') {
            http_response_code(400);
            echo json_encode(['success' => false, 'error' => 'Comment already moderated']);
            exit;
        }

        $new_status = $action === 'approve' ? 'approved' : 'rejected';

        $stmt = $blog_db->prepare("
            UPDATE comments 
            SET status = ?
            WHERE id = ?
        ");
        $stmt->execute([$new_status, $comment_id]);

        write_logs("Auto-{$action}ed comment #{$comment_id} by {$comment['author_name']} on '{$comment['article_title']}'");

        http_response_code(200);
        echo json_encode([
            'success' => true,
            'action' => $action,
            'comment_id' => $comment_id,
            'author_name' => $comment['author_name'],
            'article_title' => $comment['article_title']
        ]);
    }
} catch (PDOException $e) {
    write_logs("Database error in auto_moderate_comments.php: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Database error']);
}
