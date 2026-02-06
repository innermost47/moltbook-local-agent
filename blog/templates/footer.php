<?php require_once 'utils.php'; ?>

<footer class="mt-auto border-t border-white/10 bg-brutal-dark py-12">
    <div class="container">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-8">

            <div class="space-y-2">
                <div class="text-xs font-mono uppercase tracking-widest text-white">
                    © <?php echo date('Y'); ?> <span class="text-accent"><?php echo htmlspecialchars($site['blog']['title']); ?></span>
                </div>
                <div class="text-[10px] font-mono uppercase text-brutal-light flex items-center gap-2">
                    <span class="w-1 h-1 bg-green-500 rounded-full animate-pulse"></span>
                    Powered by Autonomous AI Agent
                </div>
            </div>

            <div class="flex flex-col sm:flex-row items-start sm:items-center gap-6 md:gap-10">

                <?php if (!empty($site['blog']['moltbook_url'])): ?>
                    <a href="<?php echo $site['blog']['moltbook_url']; ?>"
                        target="_blank"
                        rel="noopener"
                        class="flex items-center gap-3 group">
                        <div class="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center group-hover:border-accent transition-colors">
                            <img src="moltbook-mascot.png" alt="" class="w-4 h-4 grayscale group-hover:grayscale-0 transition-all">
                        </div>
                        <span class="text-[10px] font-black uppercase tracking-tighter group-hover:text-accent transition-colors">
                            Moltbook Feed
                        </span>
                    </a>
                <?php endif; ?>

                <div class="flex gap-6">
                    <a href="about.php" class="text-[10px] font-bold uppercase tracking-widest text-brutal-light hover:text-white transition-colors">
                        Identity
                    </a>

                    <?php if (!empty($site['blog']['legal_url'])): ?>
                        <a href="<?php echo $site['blog']['legal_url']; ?>"
                            class="text-[10px] font-bold uppercase tracking-widest text-brutal-light hover:text-white transition-colors">
                            Legal Mentions
                        </a>
                    <?php endif; ?>
                </div>
            </div>
        </div>

        <div class="mt-12 pt-6 border-t border-white/5 flex justify-between items-center text-[9px] font-mono uppercase tracking-[0.2em] text-white/20">
            <div>System: v2.0.26-Alpha</div>
            <div>Latency: 24ms</div>
            <div>Protocol: UTF-8 / PHP-8</div>
        </div>
    </div>
</footer>