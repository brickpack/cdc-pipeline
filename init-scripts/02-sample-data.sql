-- Insert sample data for testing CDC pipeline
-- This script populates the database with realistic test data

-- Insert sample customers
INSERT INTO customers (email, first_name, last_name, phone, address, city, state, zip_code, country) VALUES
('john.doe@example.com', 'John', 'Doe', '555-0101', '123 Main St', 'New York', 'NY', '10001', 'USA'),
('jane.smith@example.com', 'Jane', 'Smith', '555-0102', '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'USA'),
('bob.johnson@example.com', 'Bob', 'Johnson', '555-0103', '789 Pine Rd', 'Chicago', 'IL', '60601', 'USA'),
('alice.williams@example.com', 'Alice', 'Williams', '555-0104', '321 Elm St', 'Houston', 'TX', '77001', 'USA'),
('charlie.brown@example.com', 'Charlie', 'Brown', '555-0105', '654 Maple Dr', 'Phoenix', 'AZ', '85001', 'USA'),
('diana.miller@example.com', 'Diana', 'Miller', '555-0106', '987 Birch Ln', 'Philadelphia', 'PA', '19101', 'USA'),
('edward.davis@example.com', 'Edward', 'Davis', '555-0107', '147 Cedar Ct', 'San Antonio', 'TX', '78201', 'USA'),
('fiona.garcia@example.com', 'Fiona', 'Garcia', '555-0108', '258 Spruce Way', 'San Diego', 'CA', '92101', 'USA'),
('george.martinez@example.com', 'George', 'Martinez', '555-0109', '369 Willow Pl', 'Dallas', 'TX', '75201', 'USA'),
('hannah.rodriguez@example.com', 'Hannah', 'Rodriguez', '555-0110', '741 Ash Blvd', 'San Jose', 'CA', '95101', 'USA');

-- Insert sample products
INSERT INTO products (sku, name, description, category, price, cost, inventory_quantity, is_active) VALUES
('LAPTOP-001', 'Professional Laptop 15"', 'High-performance laptop with 16GB RAM and 512GB SSD', 'Electronics', 1299.99, 899.99, 50, true),
('PHONE-001', 'Smartphone Pro Max', 'Latest smartphone with advanced camera system', 'Electronics', 999.99, 699.99, 100, true),
('TABLET-001', 'Tablet Air 10"', 'Lightweight tablet perfect for entertainment', 'Electronics', 599.99, 399.99, 75, true),
('DESK-001', 'Standing Desk Adjustable', 'Electric height-adjustable standing desk', 'Furniture', 499.99, 299.99, 30, true),
('CHAIR-001', 'Ergonomic Office Chair', 'Comfortable office chair with lumbar support', 'Furniture', 349.99, 199.99, 40, true),
('MONITOR-001', '27" 4K Monitor', 'Ultra HD monitor with HDR support', 'Electronics', 449.99, 279.99, 60, true),
('KEYBOARD-001', 'Mechanical Keyboard RGB', 'Premium mechanical keyboard with RGB lighting', 'Electronics', 149.99, 79.99, 120, true),
('MOUSE-001', 'Wireless Gaming Mouse', 'Precision wireless mouse for gaming', 'Electronics', 79.99, 39.99, 150, true),
('HEADSET-001', 'Noise-Canceling Headset', 'Premium headset with active noise cancellation', 'Electronics', 249.99, 149.99, 80, true),
('WEBCAM-001', '1080p HD Webcam', 'High-definition webcam for video calls', 'Electronics', 89.99, 49.99, 100, true),
('LAMP-001', 'LED Desk Lamp', 'Adjustable LED desk lamp with USB charging', 'Furniture', 39.99, 19.99, 200, true),
('BACKPACK-001', 'Laptop Backpack', 'Water-resistant backpack with laptop compartment', 'Accessories', 79.99, 39.99, 150, true),
('CABLE-001', 'USB-C Cable 6ft', 'High-speed USB-C charging cable', 'Accessories', 19.99, 7.99, 300, true),
('ADAPTER-001', 'Multi-Port USB Adapter', 'USB-C adapter with HDMI and USB 3.0 ports', 'Accessories', 49.99, 24.99, 180, true),
('STAND-001', 'Laptop Stand Aluminum', 'Ergonomic aluminum laptop stand', 'Accessories', 59.99, 29.99, 100, true);

-- Insert sample orders
INSERT INTO orders (customer_id, order_number, order_status, total_amount, tax_amount, shipping_amount, payment_method, shipping_address, billing_address, order_date) VALUES
(1, 'ORD-2024-0001', 'delivered', 1449.98, 115.99, 0.00, 'credit_card', '123 Main St, New York, NY 10001', '123 Main St, New York, NY 10001', CURRENT_TIMESTAMP - INTERVAL '30 days'),
(2, 'ORD-2024-0002', 'delivered', 999.99, 79.99, 15.00, 'paypal', '456 Oak Ave, Los Angeles, CA 90001', '456 Oak Ave, Los Angeles, CA 90001', CURRENT_TIMESTAMP - INTERVAL '28 days'),
(3, 'ORD-2024-0003', 'shipped', 849.98, 67.99, 0.00, 'credit_card', '789 Pine Rd, Chicago, IL 60601', '789 Pine Rd, Chicago, IL 60601', CURRENT_TIMESTAMP - INTERVAL '5 days'),
(4, 'ORD-2024-0004', 'processing', 599.99, 47.99, 10.00, 'credit_card', '321 Elm St, Houston, TX 77001', '321 Elm St, Houston, TX 77001', CURRENT_TIMESTAMP - INTERVAL '2 days'),
(5, 'ORD-2024-0005', 'pending', 1699.96, 135.99, 0.00, 'credit_card', '654 Maple Dr, Phoenix, AZ 85001', '654 Maple Dr, Phoenix, AZ 85001', CURRENT_TIMESTAMP - INTERVAL '1 day');

-- Insert order items for order 1
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_amount, total_price) VALUES
(1, 1, 1, 1299.99, 0.00, 1299.99),
(1, 13, 3, 19.99, 10.00, 49.97);

-- Insert order items for order 2
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_amount, total_price) VALUES
(2, 2, 1, 999.99, 0.00, 999.99);

-- Insert order items for order 3
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_amount, total_price) VALUES
(3, 4, 1, 499.99, 0.00, 499.99),
(3, 5, 1, 349.99, 0.00, 349.99);

-- Insert order items for order 4
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_amount, total_price) VALUES
(4, 3, 1, 599.99, 0.00, 599.99);

-- Insert order items for order 5
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_amount, total_price) VALUES
(5, 6, 2, 449.99, 50.00, 849.98),
(5, 7, 2, 149.99, 0.00, 299.98),
(5, 8, 2, 79.99, 0.00, 159.98),
(5, 9, 1, 249.99, 0.00, 249.99),
(5, 11, 2, 39.99, 0.00, 79.98);

-- Insert inventory transactions
INSERT INTO inventory_transactions (product_id, transaction_type, quantity_change, reference_id, notes) VALUES
(1, 'purchase', 100, NULL, 'Initial stock purchase'),
(2, 'purchase', 150, NULL, 'Initial stock purchase'),
(3, 'purchase', 100, NULL, 'Initial stock purchase'),
(1, 'sale', -1, 1, 'Sold via order ORD-2024-0001'),
(13, 'sale', -3, 1, 'Sold via order ORD-2024-0001'),
(2, 'sale', -1, 2, 'Sold via order ORD-2024-0002'),
(4, 'sale', -1, 3, 'Sold via order ORD-2024-0003'),
(5, 'sale', -1, 3, 'Sold via order ORD-2024-0003'),
(3, 'sale', -1, 4, 'Sold via order ORD-2024-0004'),
(6, 'sale', -2, 5, 'Sold via order ORD-2024-0005'),
(7, 'sale', -2, 5, 'Sold via order ORD-2024-0005'),
(8, 'sale', -2, 5, 'Sold via order ORD-2024-0005'),
(9, 'sale', -1, 5, 'Sold via order ORD-2024-0005'),
(11, 'sale', -2, 5, 'Sold via order ORD-2024-0005');

-- Update shipped and delivered dates for completed orders
UPDATE orders SET
    shipped_date = order_date + INTERVAL '1 day',
    delivered_date = order_date + INTERVAL '4 days'
WHERE order_status = 'delivered';

UPDATE orders SET
    shipped_date = order_date + INTERVAL '1 day'
WHERE order_status = 'shipped';

-- Display summary
SELECT 'Database initialized successfully!' AS status;
SELECT COUNT(*) AS customer_count FROM customers;
SELECT COUNT(*) AS product_count FROM products;
SELECT COUNT(*) AS order_count FROM orders;
SELECT COUNT(*) AS order_item_count FROM order_items;
SELECT COUNT(*) AS inventory_transaction_count FROM inventory_transactions;
