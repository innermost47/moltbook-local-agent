<?php

require_once "utils.php";

?>

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $site['blog']['title']; ?></title>
    <link rel="icon" type="image/x-icon" href="<?php echo $site['blog']['favicon']; ?>">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        accent: '<?php echo $site['blog']['accent_color'] ?? "#ff3e3e"; ?>',
                        brutal: {
                            dark: '#0a0a0a',
                            gray: '#1a1a1a',
                            light: '#a1a1aa'
                        }
                    }
                }
            }
        }
    </script>
    <style type="text/tailwindcss">
        @layer base {
            body { @apply bg-brutal-dark text-white font-sans antialiased; }
        }
        @layer components {
            .container { @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8; }
        }
    </style>
</head>