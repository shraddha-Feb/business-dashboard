-- =========================================================
-- Business Dashboard: SQL Reporting Layer
-- Reusable views for KPIs and business metrics
-- =========================================================

-- ---------------------------------------------------------
-- 1. Daily Sales
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW daily_sales AS
SELECT
    order_date,
    SUM(sales) AS total_sales,
    COUNT(DISTINCT order_id) AS total_orders
FROM orders
GROUP BY order_date
ORDER BY order_date;

-- ---------------------------------------------------------
-- 2. Monthly Revenue
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW monthly_revenue AS
SELECT
    DATE_TRUNC('month', order_date)::DATE AS month,
    SUM(sales) AS total_sales,
    COUNT(DISTINCT order_id) AS total_orders
FROM orders
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;

-- ---------------------------------------------------------
-- 3. Top Customers (by total spend)
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW top_customers AS
SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    c.region,
    SUM(o.sales) AS total_spent,
    COUNT(DISTINCT o.order_id) AS total_orders
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name, c.segment, c.region
ORDER BY total_spent DESC;

-- ---------------------------------------------------------
-- 4. Top Products (by total revenue)
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW top_products AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    SUM(o.sales) AS total_revenue,
    COUNT(o.row_id) AS units_sold
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.sub_category
ORDER BY total_revenue DESC;

-- ---------------------------------------------------------
-- 5. Category Performance
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW category_performance AS
SELECT
    p.category,
    p.sub_category,
    SUM(o.sales) AS total_sales,
    COUNT(o.row_id) AS total_items_sold
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category, p.sub_category
ORDER BY total_sales DESC;

-- ---------------------------------------------------------
-- 6. Region Performance
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW region_performance AS
SELECT
    c.region,
    SUM(o.sales) AS total_sales,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT c.customer_id) AS total_customers
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.region
ORDER BY total_sales DESC;

-- ---------------------------------------------------------
-- 7. Running Revenue (cumulative sales over time)
--    Uses a window function: SUM() OVER (ORDER BY ...)
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW running_revenue AS
SELECT
    order_date,
    SUM(sales) AS daily_sales,
    SUM(SUM(sales)) OVER (ORDER BY order_date) AS running_total
FROM orders
GROUP BY order_date
ORDER BY order_date;

-- ---------------------------------------------------------
-- 8. Month-over-Month Growth
--    Uses a CTE + LAG() window function to compare each
--    month's revenue to the previous month's
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW mom_growth AS
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', order_date)::DATE AS month,
        SUM(sales) AS total_sales
    FROM orders
    GROUP BY DATE_TRUNC('month', order_date)
)
SELECT
    month,
    total_sales,
    LAG(total_sales) OVER (ORDER BY month) AS previous_month_sales,
    ROUND(
        ((total_sales - LAG(total_sales) OVER (ORDER BY month))
         / NULLIF(LAG(total_sales) OVER (ORDER BY month), 0)) * 100,
        2
    ) AS growth_percent
FROM monthly
ORDER BY month;

-- ---------------------------------------------------------
-- 9. Customer Retention (customers with more than 1 order)
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW customer_retention AS
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(DISTINCT o.order_id) AS total_orders,
    CASE
        WHEN COUNT(DISTINCT o.order_id) > 1 THEN 'Repeat'
        ELSE 'One-time'
    END AS customer_type
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY total_orders DESC;