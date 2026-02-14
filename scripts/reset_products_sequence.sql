-- Сброс sequence для products.id
-- Используйте этот скрипт, если получаете ошибку:
-- "duplicate key value violates unique constraint products_pkey"

-- Проверить текущее состояние
SELECT 
    'MAX ID in products' as info,
    COALESCE(MAX(id), 0) as value 
FROM products
UNION ALL
SELECT 
    'Current sequence value' as info,
    last_value as value 
FROM products_id_seq;

-- Сбросить sequence на MAX(id) + 1
SELECT setval(
    pg_get_serial_sequence('products', 'id'),
    COALESCE((SELECT MAX(id) FROM products), 0) + 1,
    false
);

-- Проверить результат
SELECT 
    'New sequence value' as info,
    last_value as value 
FROM products_id_seq;
