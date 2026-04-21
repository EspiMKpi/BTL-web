const mysql = require('mysql2/promise'); // Use the promise version
const { createClient } = require('redis');
require('dotenv').config();

// MySQL Connection Pool
const pool = mysql.createPool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
    waitForConnections: true,
    connectionLimit: 10
});

// Redis Connection
const redisClient = createClient();
redisClient.on('error', (err) => console.error('Redis Error', err));
redisClient.connect().then(() => console.log("Connected to Redis"));

module.exports = { pool, redisClient };