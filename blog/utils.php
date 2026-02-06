<?php

function write_logs($message)
{
    $timestamp = date('Y-m-d H:i:s');
    file_put_contents("access.log", "[$timestamp] $message" . PHP_EOL, FILE_APPEND);
}

function loadEnv($path)
{
    if (!file_exists($path)) {
        return false;
    }

    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos(trim($line), '#') === 0) continue;

        list($name, $value) = explode('=', $line, 2);
        $name = trim($name);
        $value = trim($value);

        $value = trim($value, '"\'');

        if (!array_key_exists($name, $_SERVER) && !array_key_exists($name, $_ENV)) {
            putenv(sprintf('%s=%s', $name, $value));
            $_ENV[$name] = $value;
            $_SERVER[$name] = $value;
        }
    }
    return true;
}



function loadYamlConfig($filename)
{
    if (!file_exists($filename)) return [];

    $config = [];
    $lines = file($filename, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    $currentSection = '';
    $currentKey = '';

    foreach ($lines as $line) {
        $trimmed = trim($line);
        if (empty($trimmed) || strpos($trimmed, '#') === 0) continue;

        if (preg_match('/^(\w+):$/', $line, $matches)) {
            $currentSection = $matches[1];
            $config[$currentSection] = [];
            continue;
        }

        if (preg_match('/^\s*-\s*["\']?(.*?)["\']?$/', $line, $matches)) {
            if ($currentSection && $currentKey) {
                if (!is_array($config[$currentSection][$currentKey])) {
                    $config[$currentSection][$currentKey] = [];
                }
                $config[$currentSection][$currentKey][] = $matches[1];
            }
            continue;
        }

        if (preg_match('/^\s+(\w+):\s*["\']?(.*?)["\']?$/', $line, $matches)) {
            $currentKey = $matches[1];
            $value = $matches[2];

            if ($currentSection) {
                $config[$currentSection][$currentKey] = $value;
            } else {
                $config[$currentKey] = $value;
            }
        }
    }
    return $config;
}


$site = loadYamlConfig(__DIR__ . '/config.yaml');

loadEnv(__DIR__ . '/.env');
