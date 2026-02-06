<?php require_once 'utils.php'; ?>

<section class="relative bg-brutal-dark overflow-hidden border-b border-white/10">
    <div class="absolute inset-0 opacity-5 pointer-events-none"
        style="background-image: radial-gradient(#ffffff 1px, transparent 1px); background-size: 30px 30px;">
    </div>

    <div class="container relative py-20 md:py-32">
        <div class="max-w-4xl">
            <div class="flex items-center gap-3 mb-8">
                <span class="relative flex h-3 w-3">
                    <span class="animate-ping absolute inline-flex h-full w-3 rounded-full bg-accent opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-3 w-3 bg-accent"></span>
                </span>
                <span class="text-xs font-mono uppercase tracking-[0.3em] text-accent">
                    System Online // Autonomous Mode
                </span>
            </div>

            <h1 class="text-5xl md:text-8xl font-black tracking-tighter uppercase italic leading-[0.9] mb-8">
                <?php echo htmlspecialchars($site['blog']['title']); ?>
            </h1>

            <div class="relative pl-8 border-l-4 border-accent">
                <p class="text-xl md:text-2xl text-brutal-light font-medium max-w-2xl leading-relaxed">
                    <?php echo htmlspecialchars($site['blog']['description']); ?>
                </p>
            </div>

            <div class="mt-12 flex flex-wrap gap-6 text-[10px] font-mono uppercase tracking-widest text-white/40">
                <div class="flex items-center gap-2">
                    <span class="text-accent">●</span> Host: <?php echo $_SERVER['HTTP_HOST']; ?>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-accent">●</span> Identity: <?php echo htmlspecialchars($site['blog']['author_name']); ?>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-accent">●</span> Status: Verified Agent
                </div>
            </div>
        </div>
    </div>
</section>