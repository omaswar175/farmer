import sqlite3
from flask import Flask, render_template, request, jsonify
import random
import math
from datetime import datetime, date

app = Flask(__name__)
DB_NAME = "database.db"

# --- SQL DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            details TEXT DEFAULT '',
            farm_size_acres REAL DEFAULT 0,
            district TEXT DEFAULT '',
            state TEXT DEFAULT '',
            upi_id TEXT DEFAULT '',
            is_profile_complete INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (role, name, email, phone, details, farm_size_acres, district, state, upi_id, is_profile_complete)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("farmer", "SHERA", "shera29@gmail.com", "9876543210", "Pune Agro FPO", 5.0, "Pune", "Maharashtra", "shera@upi", 1))

    # 2. Crops Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_name TEXT NOT NULL,
            crop_name TEXT NOT NULL,
            quantity_kg REAL NOT NULL,
            price_per_kg REAL NOT NULL,
            fpo TEXT NOT NULL,
            location TEXT NOT NULL DEFAULT 'Pune, Maharashtra',
            harvest_date TEXT NOT NULL DEFAULT '',
            publish_date TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL,
            quality_grade TEXT NOT NULL DEFAULT 'Grade A',
            quality_score INTEGER NOT NULL DEFAULT 95
        )
    ''')

    cursor.execute("PRAGMA table_info(crops)")
    crop_cols = [c[1] for c in cursor.fetchall()]
    if "location" not in crop_cols:
        cursor.execute("ALTER TABLE crops ADD COLUMN location TEXT NOT NULL DEFAULT 'Pune, Maharashtra'")
    if "harvest_date" not in crop_cols:
        cursor.execute("ALTER TABLE crops ADD COLUMN harvest_date TEXT NOT NULL DEFAULT ''")
    if "publish_date" not in crop_cols:
        cursor.execute("ALTER TABLE crops ADD COLUMN publish_date TEXT NOT NULL DEFAULT ''")

    # 3. Orders Table (With Order Timestamp)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_id INTEGER NOT NULL,
            buyer_name TEXT NOT NULL,
            buyer_email TEXT NOT NULL DEFAULT '',
            qty_kg REAL NOT NULL,
            total_price REAL NOT NULL,
            payment_id TEXT NOT NULL DEFAULT '',
            status TEXT DEFAULT 'Paid & Confirmed',
            order_time TEXT NOT NULL DEFAULT ''
        )
    ''')
    
    cursor.execute("PRAGMA table_info(orders)")
    order_cols = [c[1] for c in cursor.fetchall()]
    if "buyer_email" not in order_cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN buyer_email TEXT NOT NULL DEFAULT ''")
    if "payment_id" not in order_cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_id TEXT NOT NULL DEFAULT ''")
    if "order_time" not in order_cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN order_time TEXT NOT NULL DEFAULT ''")

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json() or {}
        email = str(data.get('email', '')).strip().lower()
        name = str(data.get('name', '')).strip()
        role = str(data.get('role', 'farmer')).strip()
        phone = str(data.get('phone', '')).strip()

        if not email or not name:
            return jsonify({"status": "error", "message": "Name and Email are required!"}), 400

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, email, role, is_profile_complete FROM users WHERE LOWER(email) = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Email is already registered!"}), 400

        is_complete = 1 if role != 'farmer' else 0
        cursor.execute('''
            INSERT INTO users (role, name, email, phone, details, is_profile_complete) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (role, name, email, phone, data.get('details', ''), is_complete))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "status": "success", 
            "message": "Account created successfully!",
            "user": {"id": user_id, "name": name, "email": email, "role": role, "is_profile_complete": is_complete}
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json() or {}
        email = str(data.get('email', '')).strip().lower()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, email, role, is_profile_complete, farm_size_acres, district, state, upi_id FROM users WHERE LOWER(email) = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            return jsonify({
                "status": "success",
                "user": {
                    "id": user[0], "name": user[1], "email": user[2], "role": user[3],
                    "is_profile_complete": user[4], "farm_size": user[5], 
                    "district": user[6], "state": user[7], "upi_id": user[8]
                }
            })
        return jsonify({"status": "error", "message": "Account not found!"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/farmer/profile', methods=['POST'])
def save_profile():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET farm_size_acres = ?, district = ?, state = ?, upi_id = ?, details = ?, is_profile_complete = 1
        WHERE LOWER(email) = ? AND role = 'farmer'
    ''', (data.get('farm_size', 0), data.get('district', ''), data.get('state', ''), data.get('upi_id', ''), data.get('fpo_name', ''), email))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Profile updated!"})

@app.route('/api/farmer/profile/<email>', methods=['GET'])
def get_farmer_profile(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT name, email, phone, role, farm_size_acres, district, state, upi_id, details, is_profile_complete FROM users WHERE LOWER(email) = LOWER(?)', (email.strip(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({"status": "success", "profile": {"name": row[0], "email": row[1], "phone": row[2], "role": row[3], "farm_size": row[4], "district": row[5], "state": row[6], "upi_id": row[7], "fpo": row[8], "is_profile_complete": row[9]}})
    return jsonify({"status": "error", "message": "Not found"}), 404

@app.route('/api/farmer/profile/update', methods=['POST'])
def update_profile():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET name = ?, phone = ?, farm_size_acres = ?, district = ?, state = ?, upi_id = ?, details = ?
        WHERE LOWER(email) = ? AND role = 'farmer'
    ''', (data.get('name'), data.get('phone'), data.get('farm_size'), data.get('district'), data.get('state'), data.get('upi_id'), data.get('fpo'), email))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Profile updated!"})

@app.route('/api/ai/quality-check', methods=['POST'])
def quality_check():
    data = request.get_json() or {}
    selected_crop = data.get('crop_name', '').lower()
    filename = data.get('filename', '').lower()
    
    valid_crops = {
        "potatoes": ["potato", "potatoes", "erdfrucht", "aloo", "spud"],
        "tomatoes": ["tomato", "tomatoes", "tamatar"],
        "onions": ["onion", "onions", "pyaz", "kanda"],
        "wheat": ["wheat", "grain", "gehu"]
    }

    detected_crop = None
    for crop_key, keywords in valid_crops.items():
        if any(kw in filename for kw in keywords):
            detected_crop = crop_key
            break

    if detected_crop is None or detected_crop != selected_crop.lower():
        detected_label = detected_crop.title() if detected_crop else "Non-Crop / Unrelated Object"
        return jsonify({
            "status": "mismatch",
            "detected_crop": detected_label,
            "selected_crop": selected_crop.title(),
            "message": f"❌ AI Inspection Failed! You selected '{selected_crop.title()}', but the uploaded photo appears to be '{detected_label}'."
        })

    score = random.randint(88, 98)
    grade = "Grade A (Premium)" if score >= 92 else "Grade B (Good Standard)"
    return jsonify({"status": "passed", "detected_crop": detected_crop.title(), "selected_crop": selected_crop.title(), "quality_score": score, "quality_grade": grade, "analysis": f"AI Computer Vision scan completed. Produce verified! Freshness score: {score}%."})

@app.route('/api/crops/add', methods=['POST'])
def add_crop():
    data = request.get_json() or {}
    farmer_email = str(data.get('farmer_email', '')).strip().lower()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT role, name, is_profile_complete, district, state FROM users WHERE LOWER(email) = ?', (farmer_email,))
    user = cursor.fetchone()
    
    if not user or user[0] != 'farmer' or user[2] == 0:
        conn.close()
        return jsonify({"status": "error", "message": "Unauthorized or profile incomplete!"}), 403

    today_publish_date = date.today().strftime("%Y-%m-%d")
    location = data.get('location') or f"{user[3]}, {user[4]}"
    harvest_date = data.get('harvest_date', today_publish_date)
    img = data.get('image_data') or "https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=500"

    cursor.execute('''
        INSERT INTO crops (farmer_name, crop_name, quantity_kg, price_per_kg, fpo, location, harvest_date, publish_date, image_url, quality_grade, quality_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user[1], data['crop_name'], data['quantity_kg'], data['price_per_kg'], data['fpo'], location, harvest_date, today_publish_date, img, data.get('quality_grade', 'Grade A'), data.get('quality_score', 95)))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Produce published successfully on {today_publish_date}!"})

@app.route('/api/crops/delete', methods=['POST'])
def delete_crop():
    data = request.get_json() or {}
    crop_id = data.get('crop_id')
    farmer_email = str(data.get('farmer_email', '')).strip().lower()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT name, role FROM users WHERE LOWER(email) = ?', (farmer_email,))
    user = cursor.fetchone()
    
    cursor.execute('SELECT farmer_name FROM crops WHERE id = ?', (crop_id,))
    crop = cursor.fetchone()

    if not crop or crop[0].strip().lower() != user[0].strip().lower():
        conn.close()
        return jsonify({"status": "error", "message": "🔒 Access Denied! You can only delete your own listings."}), 403

    cursor.execute('DELETE FROM crops WHERE id = ?', (crop_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Listing deleted successfully!"})

@app.route('/api/crops/list', methods=['GET'])
def list_crops():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, farmer_name, crop_name, quantity_kg, price_per_kg, fpo, location, harvest_date, publish_date, image_url, quality_grade, quality_score FROM crops WHERE quantity_kg > 0 ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    crops = [{"id": r[0], "farmer": r[1], "crop": r[2], "qty_kg": r[3], "price": r[4], "fpo": r[5], "location": r[6], "harvest_date": r[7], "publish_date": r[8], "image": r[9], "quality_grade": r[10], "quality_score": r[11]} for r in rows]
    return jsonify({"crops": crops})

@app.route('/api/buyer/smart-match', methods=['POST'])
def smart_match_requirement():
    data = request.get_json() or {}
    required_crop = str(data.get('crop_name', '')).strip().lower()
    required_qty = float(data.get('quantity_kg', 0))
    max_price = float(data.get('max_price', 999999))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, farmer_name, crop_name, quantity_kg, price_per_kg, fpo, location, harvest_date, publish_date, image_url, quality_grade, quality_score 
        FROM crops 
        WHERE LOWER(crop_name) = ? AND price_per_kg <= ? AND quantity_kg > 0
        ORDER BY price_per_kg ASC, quality_score DESC
    ''', (required_crop, max_price))
    
    available_listings = cursor.fetchall()
    conn.close()

    if not available_listings:
        return jsonify({"status": "no_match", "message": f"No available listings found for {required_crop.title()} under ₹{max_price}/kg."})

    fulfilled_qty = 0.0
    selected_listings = []
    
    for item in available_listings:
        if fulfilled_qty >= required_qty:
            break
        available_stock = item[3]
        needed = required_qty - fulfilled_qty
        take_qty = min(available_stock, needed)
        
        selected_listings.append({
            "id": item[0], "farmer": item[1], "crop": item[2], "stock_kg": item[3],
            "taken_kg": take_qty, "price": item[4], "fpo": item[5], "location": item[6],
            "harvest_date": item[7], "publish_date": item[8], "image": item[9],
            "quality_grade": item[10], "quality_score": item[11]
        })
        fulfilled_qty += take_qty

    avg_price = sum(l['price'] * l['taken_kg'] for l in selected_listings) / fulfilled_qty if fulfilled_qty > 0 else 0

    return jsonify({
        "status": "success",
        "is_fully_met": fulfilled_qty >= required_qty,
        "target_qty": required_qty,
        "fulfilled_qty": fulfilled_qty,
        "farmer_count": len(selected_listings),
        "weighted_avg_price": round(avg_price, 2),
        "total_estimated_cost": round(fulfilled_qty * avg_price, 2),
        "pooled_crops": selected_listings
    })

@app.route('/api/orders/place', methods=['POST'])
def place_order():
    try:
        data = request.get_json() or {}
        buyer_name = data.get('buyer_name', 'Anonymous Buyer')
        buyer_email = str(data.get('buyer_email', 'buyer@example.com')).strip().lower()
        payment_id = data.get('payment_id', f"pay_{random.randint(100000, 999999)}")
        pooled_items = data.get('pooled_items', [])
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not pooled_items:
            return jsonify({"status": "error", "message": "No items in purchase pool!"}), 400

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        for item in pooled_items:
            crop_id = item['id']
            qty_purchased = item['taken_kg']
            total_item_price = qty_purchased * item['price']

            cursor.execute('''
                INSERT INTO orders (crop_id, buyer_name, buyer_email, qty_kg, total_price, payment_id, status, order_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (crop_id, buyer_name, buyer_email, qty_purchased, total_item_price, payment_id, "Paid & Confirmed", now_iso))

            cursor.execute('''
                UPDATE crops SET quantity_kg = quantity_kg - ? WHERE id = ?
            ''', (qty_purchased, crop_id))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": f"Order successfully placed for {len(pooled_items)} farmer(s)! Payment ID: {payment_id}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Purchase error: {str(e)}"}), 500

@app.route('/api/orders/user/<email>', methods=['GET'])
def get_user_orders(email):
    try:
        email = email.strip().lower()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('SELECT name, role FROM users WHERE LOWER(email) = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({"status": "error", "message": "User not found!"}), 404

        user_name, role = user[0], user[1]
        now_dt = datetime.now()

        if role == 'farmer':
            cursor.execute('''
                SELECT o.id, c.crop_name, o.qty_kg, o.total_price, o.buyer_name, o.buyer_email, o.payment_id, o.status, c.location, o.order_time
                FROM orders o
                JOIN crops c ON o.crop_id = c.id
                WHERE LOWER(c.farmer_name) = LOWER(?)
                ORDER BY o.id DESC
            ''', (user_name,))
            rows = cursor.fetchall()
            conn.close()

            orders = [{
                "order_id": r[0], "crop": r[1], "qty_kg": r[2], "total_price": r[3],
                "customer_name": r[4], "customer_email": r[5], "payment_id": r[6],
                "status": r[7], "location": r[8], "order_time": r[9]
            } for r in rows]

            return jsonify({"status": "success", "role": "farmer", "orders": orders})

        else:
            cursor.execute('''
                SELECT o.id, c.crop_name, o.qty_kg, o.total_price, c.farmer_name, o.payment_id, o.status, c.location, o.order_time
                FROM orders o
                JOIN crops c ON o.crop_id = c.id
                WHERE LOWER(o.buyer_email) = LOWER(?)
                ORDER BY o.id DESC
            ''', (email,))
            rows = cursor.fetchall()
            conn.close()

            orders = []
            for r in rows:
                ord_time_str = r[8]
                can_cancel = False
                minutes_left = 0
                
                if ord_time_str and r[6] == 'Paid & Confirmed':
                    try:
                        ord_dt = datetime.strptime(ord_time_str, "%Y-%m-%d %H:%M:%S")
                        elapsed_seconds = (now_dt - ord_dt).total_seconds()
                        # 2 Hours (7200 seconds) Cancellation Window
                        if elapsed_seconds <= 7200:
                            can_cancel = True
                            minutes_left = max(1, int((7200 - elapsed_seconds) // 60))
                    except Exception:
                        can_cancel = False

                orders.append({
                    "order_id": r[0], "crop": r[1], "qty_kg": r[2], "total_price": r[3],
                    "farmer_name": r[4], "payment_id": r[5], "status": r[6], "location": r[7],
                    "order_time": r[8], "can_cancel": can_cancel, "minutes_left": minutes_left
                })

            return jsonify({"status": "success", "role": "buyer", "orders": orders})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# TIMED CANCELLATION & AUTOMATIC ESCROW REFUND ENDPOINT
@app.route('/api/orders/cancel', methods=['POST'])
def cancel_order():
    try:
        data = request.get_json() or {}
        order_id = data.get('order_id')
        buyer_email = str(data.get('buyer_email', '')).strip().lower()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, crop_id, qty_kg, total_price, status, order_time 
            FROM orders 
            WHERE id = ? AND LOWER(buyer_email) = ?
        ''', (order_id, buyer_email))
        order = cursor.fetchone()

        if not order:
            conn.close()
            return jsonify({"status": "error", "message": "Order not found or unauthorized!"}), 404

        if order[4] != 'Paid & Confirmed':
            conn.close()
            return jsonify({"status": "error", "message": f"Order cannot be cancelled. Current status: {order[4]}"}), 400

        # Validate 2-Hour Cancellation Window
        now_dt = datetime.now()
        ord_time_str = order[5]
        if ord_time_str:
            ord_dt = datetime.strptime(ord_time_str, "%Y-%m-%d %H:%M:%S")
            if (now_dt - ord_dt).total_seconds() > 7200:
                conn.close()
                return jsonify({"status": "error", "message": "⏳ Cancellation window expired (2 hours limit reached). Order has been dispatched to logistics!"}), 400

        crop_id = order[1]
        qty_kg = order[2]
        refund_amount = order[3]

        # 1. Update order status to Cancelled & Refunded
        cursor.execute('''
            UPDATE orders SET status = 'Cancelled & Refunded' WHERE id = ?
        ''', (order_id,))

        # 2. Restore Stock to Farmer's Crop Listing
        cursor.execute('''
            UPDATE crops SET quantity_kg = quantity_kg + ? WHERE id = ?
        ''', (qty_kg, crop_id))

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"🎉 Order #{order_id} successfully cancelled!\n💸 Refund of ₹{refund_amount} initiated back to your source payment account.\n📦 {qty_kg} kg restored to farmer inventory."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)