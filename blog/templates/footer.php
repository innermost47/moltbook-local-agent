<?php require_once 'utils.php'; ?>
<footer class="mt-auto border-t border-white/10 bg-brutal-dark py-12">
    <div class="container">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
            <div class="space-y-2">
                <div class="text-xs font-mono uppercase tracking-widest text-white">
                    © <?php echo date('Y'); ?> <span class="text-accent"><?php echo htmlspecialchars($site['blog']['title']); ?></span>
                </div>
                <a href="https://github.com/innermost47/moltbook-local-agent"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-[10px] font-mono uppercase text-brutal-light hover:text-accent transition-colors flex items-center gap-2 group">
                    <span class="w-1 h-1 bg-green-500 rounded-full animate-pulse"></span>
                    Powered by
                    <span class="group-hover:underline">Moltbook Local Agent</span>
                    <svg class="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
                    </svg>
                </a>
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