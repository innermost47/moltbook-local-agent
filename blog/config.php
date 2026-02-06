<?php

require_once 'utils.php';

$api_key = $_ENV['MOLTBOOK_LOCAL_AGENT_BLOG_API_KEY'];
$blog_base_url = $_ENV["MOLTBOOK_LOCAL_AGENT_BLOG_BASE_URL"];

define('DB_PATH', __DIR__ . '/blog.db');
define('MOLTBOOK_LOCAL_AGENT_BLOG_BASE_URL', $blog_base_url);
define('MOLTBOOK_LOCAL_AGENT_BLOG_API_KEY', $api_key);
define('COMMENT_KEYS_DB_PATH', __DIR__ . '/comment_keys.db');

function init_database()
{
    if (!file_exists(DB_PATH)) {
        $db = new PDO('sqlite:' . DB_PATH);
        $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        $db->exec("
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                excerpt TEXT NOT NULL,
                content TEXT NOT NULL,
                image_data TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'published',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ");

        $db->exec("
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        ");

        $db->exec("CREATE INDEX idx_articles_slug ON articles(slug)");
        $db->exec("CREATE INDEX idx_articles_status ON articles(status)");
        $db->exec("CREATE INDEX idx_comments_article ON comments(article_id)");
        $db->exec("CREATE INDEX idx_comments_status ON comments(status)");
    }

    if (!file_exists(COMMENT_KEYS_DB_PATH)) {
        $db = new PDO('sqlite:' . COMMENT_KEYS_DB_PATH);
        $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        $db->exec("
            CREATE TABLE key_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                agent_name TEXT NOT NULL,
                agent_description TEXT,
                contact_email TEXT,
                status TEXT DEFAULT 'pending',
                api_key TEXT,
                created_at TEXT NOT NULL,
                approved_at TEXT
            )
        ");

        $db->exec("
            CREATE TABLE api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL UNIQUE,
                agent_name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                comment_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_used_at TEXT
            )
        ");

        $db->exec("CREATE INDEX idx_key_requests_status ON key_requests(status)");
        $db->exec("CREATE INDEX idx_api_keys_key ON api_keys(api_key)");
    }
}

init_database();
