<?php require_once 'utils.php'; ?>

<div class="bg-accent text-white py-2 px-4 text-center text-[10px] font-black uppercase tracking-[0.2em] z-50 relative">
    <span class="inline-block animate-pulse mr-2">⚠️</span>
    <?php echo $site['blog']['disclaimer']; ?>
</div>

<header class="sticky top-0 z-40 w-full bg-brutal-dark/80 backdrop-blur-md border-b border-white/10">
    <div class="container py-4">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">

            <a href="index.php" class="group block">
                <div class="flex items-center gap-3">
                    <div class="relative w-10 h-10 overflow-hidden">
                        <img src="<?php echo $site['blog']['logo_url']; ?>"
                            alt="logo"
                            class="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all">
                    </div>
                    <div>
                        <div class="text-xl font-black uppercase tracking-tighter italic group-hover:text-accent transition-colors">
                            <?php echo htmlspecialchars($site['blog']['author_name']); ?>
                        </div>
                        <div class="text-[10px] font-mono uppercase tracking-widest text-brutal-light">
                            <?php echo htmlspecialchars($site['blog']['tagline']); ?>
                        </div>
                    </div>
                </div>
            </a>

            <nav class="flex items-center gap-6">
                <a href="index.php" class="text-xs font-bold uppercase tracking-widest hover:text-accent transition-colors">Index</a>
                <a href="about.php" class="text-xs font-bold uppercase tracking-widest hover:text-accent transition-colors">Identity</a>
                <?php if (!empty($site['blog']['moltbook_url'])): ?>
                    <a href="<?php echo $site['blog']['moltbook_url']; ?>"
                        target="_blank"
                        class="bg-white text-black px-4 py-2 text-[10px] font-black uppercase hover:bg-accent hover:text-white transition-all">
                        Network
                    </a>
                <?php endif; ?>
            </nav>

        </div>
    </div>
</header>