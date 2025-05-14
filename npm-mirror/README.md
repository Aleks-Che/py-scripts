# NPM Mirror

скрипты для создания локального зеркала npm пакетов

1. npm install из каталога npm-mirror
2. создание списка пакетов npm run scripts/fetch-packages-by-query.js
3. объединение полученных списков с удалением дубликатов npm run scripts/merge-search-results.js
4. скачивание всех библиотек на основе готового списка npm run scripts/npm-mirror.js

скрипты count-packages и compare-package-counts для отслеживания изменения количества пакетов
