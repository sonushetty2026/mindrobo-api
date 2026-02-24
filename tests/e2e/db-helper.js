const { Client } = require('pg');

const DB_URL = 'postgresql://mindroboadmin:MindR0bo%23Dev2026%21@mindrobo-postgres-dev.postgres.database.azure.com/mindrobo_db?sslmode=verify-full';

class DBHelper {
  constructor() {
    this.client = null;
  }

  async connect() {
    this.client = new Client({ connectionString: DB_URL });
    await this.client.connect();
  }

  async disconnect() {
    if (this.client) await this.client.end();
  }

  async query(sql, params = []) {
    const result = await this.client.query(sql, params);
    return result.rows;
  }

  async getUserByEmail(email) {
    const rows = await this.query('SELECT * FROM users WHERE email = $1', [email]);
    return rows[0] || null;
  }

  async getBusinessById(id) {
    const rows = await this.query('SELECT * FROM businesses WHERE id = $1::uuid', [id]);
    return rows[0] || null;
  }

  async deleteTestUser(email) {
    // First get user id
    const user = await this.getUserByEmail(email);
    if (!user) return;
    // Delete notifications for this user
    await this.query('DELETE FROM notifications WHERE user_id = $1::uuid', [user.id]);
    // Delete the user
    await this.query('DELETE FROM users WHERE id = $1::uuid', [user.id]);
  }

  async deleteTestBusiness(name) {
    const rows = await this.query('SELECT id FROM businesses WHERE name = $1', [name]);
    if (rows.length === 0) return;
    const bizId = rows[0].id;
    await this.query('DELETE FROM leads WHERE business_id = $1::uuid', [bizId]);
    await this.query('DELETE FROM businesses WHERE id = $1::uuid', [bizId]);
  }
}

module.exports = { DBHelper };
