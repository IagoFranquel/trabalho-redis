-- =====================================================================
-- Dados iniciais para teste
-- =====================================================================
INSERT INTO clientes (nome, email, categoria) VALUES
    ('Ana Souza',      'ana@email.com',    'VIP'),
    ('Bruno Lima',     'bruno@email.com',  'REGULAR'),
    ('Carla Mendes',   'carla@email.com',  'REGULAR'),
    ('Diego Ferreira', 'diego@email.com',  'VIP'),
    ('Elisa Rocha',    'elisa@email.com',  'REGULAR');

INSERT INTO produtos (nome, preco, estoque, estoque_minimo) VALUES
    ('Teclado Mecânico',    250.00, 20, 5),
    ('Mouse Gamer',         120.00, 30, 8),
    ('Monitor 24"',         899.90, 10, 3),
    ('Headset USB',         180.00, 15, 5),
    ('Webcam Full HD',      210.00,  6, 5),
    ('Cabo HDMI 2m',         25.00, 50, 10),
    ('Pen Drive 64GB',       45.00,  4, 5),
    ('Hub USB-C',           139.90,  0, 3);
