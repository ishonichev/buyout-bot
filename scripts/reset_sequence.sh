#!/bin/bash
# Скрипт для автоматического сброса sequence для products.id

echo "=== Сброс sequence для products.id ==="
echo ""

# Проверка текущего состояния
echo "🔍 Проверка текущего состояния..."
docker-compose exec postgres psql -U postgres -d buyout_bot -c "
SELECT 
    'MAX ID in products' as info,
    COALESCE(MAX(id), 0) as value 
FROM products
UNION ALL
SELECT 
    'Current sequence value' as info,
    last_value as value 
FROM products_id_seq;
"

echo ""
echo "🔧 Сбрасываем sequence..."

# Сброс sequence
docker-compose exec postgres psql -U postgres -d buyout_bot -c "
SELECT setval(
    pg_get_serial_sequence('products', 'id'),
    COALESCE((SELECT MAX(id) FROM products), 0) + 1,
    false
);
"

echo ""
echo "✅ Проверка результата..."
docker-compose exec postgres psql -U postgres -d buyout_bot -c "
SELECT 
    'New sequence value' as info,
    last_value as value 
FROM products_id_seq;
"

echo ""
echo "✅ Готово! Теперь можно добавлять новые товары."
echo ""
