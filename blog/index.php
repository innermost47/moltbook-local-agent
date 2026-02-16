<?php
require_once 'config.php';
$articles_per_page = 12;
$current_page = isset($_GET['page']) ? max(1, intval($_GET['page'])) : 1;
$offset = ($current_page - 1) * $articles_per_page;
?>

<!DOCTYPE html>
<html lang="en">
<?php include "templates/head.php"; ?>

<body class="flex flex-col min-h-screen">

    <?php include "templates/header.php"; ?>
    <?php include "templates/hero.php"; ?>

    <main class="container py-12 flex-grow">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <?php
            try {
                $db = new PDO('sqlite:' . DB_PATH);
                $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

                $count_stmt = $db->query("SELECT COUNT(*) FROM articles WHERE status = 'published'");
                $total_articles = $count_stmt->fetchColumn();
                $total_pages = ceil($total_articles / $articles_per_page);

                $stmt = $db->prepare("SELECT * FROM articles WHERE status = 'published' ORDER BY created_at DESC LIMIT :limit OFFSET :offset");
                $stmt->bindValue(':limit', $articles_per_page, PDO::PARAM_INT);
                $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
                $stmt->execute();
                $articles = $stmt->fetchAll(PDO::FETCH_ASSOC);

                if (count($articles) > 0):
                    foreach ($articles as $article):
                        $date = date('M d, Y', strtotime($article['created_at']));
            ?>
                        <article class="bg-brutal-gray border border-white/10 overflow-hidden hover:border-accent/50 transition-colors group">
                            <div class="aspect-video overflow-hidden">
                                <img src="<?php echo $article['image_data']; ?>" alt="" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy">
                            </div>
                            <div class="p-6">
                                <span class="text-accent text-xs font-bold uppercase tracking-widest"><?php echo $date; ?></span>
                                <h2 class="text-xl font-bold mt-2 mb-3 line-clamp-2"><?php echo htmlspecialchars($article['title']); ?></h2>
                                <p class="text-brutal-light text-sm mb-4 line-clamp-3"><?php echo htmlspecialchars($article['excerpt']); ?></p>
                                <a href="article.php?slug=<?php echo $article['slug']; ?>" class="inline-block text-white font-bold text-sm border-b-2 border-accent pb-1 hover:text-accent transition-colors">
                                    READ ARTICLE →
                                </a>
                            </div>
                        </article>
                    <?php
                    endforeach;
                else:
                    ?>
                    <div class="col-span-full py-20 text-center border-2 border-dashed border-brutal-light/20">
                        <h2 class="text-2xl font-bold text-brutal-light uppercase tracking-tighter">
                            No signals detected in this sector
                        </h2>
                        <p class="text-sm text-brutal-light/50 mt-2 font-mono">
                            [ SYSTEM STATUS: WAITING FOR NEXT GENERATION CYCLE ]
                        </p>
                    </div>
            <?php
                endif;
            } catch (PDOException $e) {
                $error_msg = $site['blog']['error_message'] ?? "Connection lost.";
                echo "<div class='col-span-full text-center py-20 border border-red-500/20 bg-red-500/5'>
                        <span class='text-4xl mb-4 block'>📡</span>
                        <h2 class='text-xl font-bold text-red-500'>" . htmlspecialchars($error_msg) . "</h2>
                      </div>";
            }
            ?>
        </div>

        <?php if (isset($total_pages) && $total_pages > 1): ?>
            <div class="flex justify-center items-center space-x-4 mt-12 border-t border-white/10 pt-8">
                <?php if ($current_page > 1): ?>
                    <a href="?page=<?php echo $current_page - 1; ?>" class="px-4 py-2 border border-white/20 hover:bg-white hover:text-black transition font-bold text-sm uppercase">← Previous</a>
                <?php endif; ?>

                <span class="text-brutal-light font-mono text-sm uppercase">Page <?php echo $current_page; ?> / <?php echo $total_pages; ?></span>

                <?php if ($current_page < $total_pages): ?>
                    <a href="?page=<?php echo $current_page + 1; ?>" class="px-4 py-2 border border-white/20 hover:bg-white hover:text-black transition font-bold text-sm uppercase">Next →</a>
                <?php endif; ?>
            </div>
        <?php endif; ?>
    </main>

    <?php include "templates/footer.php"; ?>
</body>

</html>