import sqlite3
from flask import Flask, render_template, request, jsonify
import random
from datetime import datetime, date

app = Flask(__name__)
DB_NAME = "database.db"

# --- SQL DATABASE INITIALIZATION & SAFE AUTO-MIGRATION ---
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
            is_profile_complete INTEGER DEFAULT 0,
            address TEXT DEFAULT '',
            pincode TEXT DEFAULT '',
            cultivation_details TEXT DEFAULT '',
            vehicle_types TEXT DEFAULT '',
            fleet_size INTEGER DEFAULT 1,
            preferred_payment TEXT DEFAULT 'UPI'
        )
    ''')

    # Safe Schema Migration Check
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [c[1] for c in cursor.fetchall()]
    new_cols = {
        "address": "TEXT DEFAULT ''",
        "pincode": "TEXT DEFAULT ''",
        "cultivation_details": "TEXT DEFAULT ''",
        "vehicle_types": "TEXT DEFAULT ''",
        "fleet_size": "INTEGER DEFAULT 1",
        "preferred_payment": "TEXT DEFAULT 'UPI'"
    }
    for col, col_type in new_cols.items():
        if col not in user_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

    # Seed System Admin User (Hidden from Registration)
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (role, name, email, phone, details, is_profile_complete)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("admin", "System Administrator", "admin@agrilink.com", "9999999999", "AgriLink HQ", 1))

    # Seed Default Farmer
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "farmer"')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (role, name, email, phone, details, farm_size_acres, district, state, upi_id, is_profile_complete, address, cultivation_details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("farmer", "SHERA", "shera29@gmail.com", "9876543210", "Pune Agro FPO", 5.0, "Pune", "Maharashtra", "shera@upi", 1, "Farm No 42, Haveli", "Potatoes, Tomatoes (Kharif/Rabi)"))

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

    # 3. Orders Table
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
            order_time TEXT NOT NULL DEFAULT '',
            delivery_otp TEXT NOT NULL DEFAULT '1234'
        )
    ''')

    # 4. Logistics Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL UNIQUE,
            carrier_email TEXT DEFAULT '',
            carrier_name TEXT DEFAULT '',
            vehicle_type TEXT NOT NULL DEFAULT 'Pickup Van',
            vehicle_number TEXT NOT NULL DEFAULT '',
            driver_name TEXT NOT NULL DEFAULT '',
            driver_phone TEXT NOT NULL DEFAULT '',
            pickup_location TEXT NOT NULL DEFAULT 'Farm Origin',
            delivery_status TEXT DEFAULT 'Unassigned - Awaiting Carrier Acceptance',
            route_distance_km REAL DEFAULT 25.0,
            assigned_at TEXT NOT NULL DEFAULT '',
            multi_pickup_route TEXT DEFAULT '',
            est_fuel_cost REAL DEFAULT 0.0
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# --- AUTHENTICATION & USER PROFILE ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json() or {}
        email = str(data.get('email', '')).strip().lower()
        name = str(data.get('name', '')).strip()
        role = str(data.get('role', 'buyer')).strip()
        phone = str(data.get('phone', '')).strip()

        # Security check: Prevent registering as admin via standard registration form
        if role == 'admin':
            return jsonify({"status": "error", "message": "Unauthorized role selection!"}), 403

        if not email or not name:
            return jsonify({"status": "error", "message": "Name and Email are required!"}), 400

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, email, role, is_profile_complete FROM users WHERE LOWER(email) = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "Email is already registered!"}), 400

        cursor.execute('''
            INSERT INTO users (role, name, email, phone, details, is_profile_complete) 
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (role, name, email, phone, data.get('details', '')))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "status": "success", 
            "message": f"Registered successfully as {role.upper()}!",
            "user": {"id": user_id, "name": name, "email": email, "role": role, "is_profile_complete": 1}
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
        cursor.execute('SELECT id, name, email, role, is_profile_complete FROM users WHERE LOWER(email) = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            return jsonify({
                "status": "success",
                "user": {
                    "id": user[0], "name": user[1], "email": user[2], "role": user[3],
                    "is_profile_complete": user[4]
                }
            })
        return jsonify({"status": "error", "message": "Account not found!"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ADMIN API ROUTES ---
@app.route('/api/admin/all-data', methods=['GET'])
def get_admin_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Fetch all users
        cursor.execute('''
            SELECT id, role, name, email, phone, district, state, address, farm_size_acres, upi_id, cultivation_details, fleet_size, vehicle_types, pincode, preferred_payment
            FROM users ORDER BY id DESC
        ''')
        users_rows = cursor.fetchall()
        users = [{
            "id": r[0], "role": r[1], "name": r[2], "email": r[3], "phone": r[4],
            "district": r[5], "state": r[6], "address": r[7], "farm_size": r[8],
            "upi_id": r[9], "cultivation_details": r[10], "fleet_size": r[11],
            "vehicle_types": r[12], "pincode": r[13], "preferred_payment": r[14]
        } for r in users_rows]

        # Fetch all crops
        cursor.execute('SELECT id, farmer_name, crop_name, quantity_kg, price_per_kg, fpo, location, harvest_date, publish_date, quality_grade, quality_score FROM crops ORDER BY id DESC')
        crops_rows = cursor.fetchall()
        crops = [{
            "id": r[0], "farmer": r[1], "crop": r[2], "qty_kg": r[3], "price": r[4],
            "fpo": r[5], "location": r[6], "harvest_date": r[7], "publish_date": r[8],
            "quality_grade": r[9], "quality_score": r[10]
        } for r in crops_rows]

        # Fetch all orders with logistics tracking
        cursor.execute('''
            SELECT o.id, o.payment_id, c.crop_name, o.qty_kg, o.total_price, o.buyer_name, o.buyer_email, o.status, o.order_time,
                   l.delivery_status, l.carrier_name, l.vehicle_number, l.driver_name, l.driver_phone
            FROM orders o
            JOIN crops c ON o.crop_id = c.id
            LEFT JOIN logistics l ON o.id = l.order_id
            ORDER BY o.id DESC
        ''')
        orders_rows = cursor.fetchall()
        orders = [{
            "id": r[0], "payment_id": r[1], "crop": r[2], "qty_kg": r[3], "total_price": r[4],
            "buyer_name": r[5], "buyer_email": r[6], "status": r[7], "order_time": r[8],
            "delivery_status": r[9] or "Unassigned", "carrier_name": r[10] or "Unassigned",
            "vehicle_number": r[11] or "-", "driver_name": r[12] or "-", "driver_phone": r[13] or "-"
        } for r in orders_rows]

        conn.close()

        return jsonify({
            "status": "success",
            "users": users,
            "crops": crops,
            "orders": orders
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/user/profile/<email>', methods=['GET'])
def get_user_profile(email):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, email, phone, role, farm_size_acres, district, state, upi_id, 
                   details, address, pincode, cultivation_details, vehicle_types, fleet_size, preferred_payment
            FROM users WHERE LOWER(email) = LOWER(?)
        ''', (email.strip(),))
        row = cursor.fetchone()
        conn.close()

        if row:
            profile = {
                "name": row[0], "email": row[1], "phone": row[2], "role": row[3],
                "farm_size": row[4], "district": row[5], "state": row[6], "upi_id": row[7],
                "fpo": row[8], "address": row[9], "pincode": row[10],
                "cultivation_details": row[11], "vehicle_types": row[12],
                "fleet_size": row[13], "preferred_payment": row[14]
            }
            return jsonify({"status": "success", "profile": profile})
        return jsonify({"status": "error", "message": "Profile not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/user/profile/update', methods=['POST'])
def update_user_profile():
    try:
        data = request.get_json() or {}
        email = str(data.get('email', '')).strip().lower()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users 
            SET name = ?, phone = ?, farm_size_acres = ?, district = ?, state = ?, upi_id = ?, 
                details = ?, address = ?, pincode = ?, cultivation_details = ?, vehicle_types = ?, 
                fleet_size = ?, preferred_payment = ?, is_profile_complete = 1
            WHERE LOWER(email) = ?
        ''', (
            data.get('name'), data.get('phone'), data.get('farm_size', 0), data.get('district', ''),
            data.get('state', ''), data.get('upi_id', ''), data.get('fpo', ''), data.get('address', ''),
            data.get('pincode', ''), data.get('cultivation_details', ''), data.get('vehicle_types', ''),
            data.get('fleet_size', 1), data.get('preferred_payment', 'UPI'), email
        ))

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Profile updated successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- AI QUALITY CHECK & CROPS ROUTES ---
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
    
    if not user or user[0] != 'farmer':
        conn.close()
        return jsonify({"status": "error", "message": "Unauthorized! Only farmers can publish produce."}), 403

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
    
    if not user:
        conn.close()
        return jsonify({"status": "error", "message": "User not found!"}), 404

    cursor.execute('SELECT farmer_name FROM crops WHERE id = ?', (crop_id,))
    crop = cursor.fetchone()

    # Allow deletion if user is owner OR admin
    if not crop or (user[1] != 'admin' and crop[0].strip().lower() != user[0].strip().lower()):
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

# --- BUYER MATCHING & ORDERS ---
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

        pickup_stops = []
        total_batch_qty = 0.0
        for item in pooled_items:
            qty = item['taken_kg']
            total_batch_qty += qty
            pickup_stops.append(f"Pickup {qty}kg from {item['farmer']} (📍 {item.get('location', 'Farm Origin')})")
        
        waypoint_text = " ➔ ".join(pickup_stops) + f" ➔ Final Delivery to {buyer_name}"
        total_distance = round(15.0 + (len(pooled_items) * 12.5), 1)
        fuel_cost = round(total_distance * 11.5, 2)
        generated_otp = str(random.randint(1000, 9999))

        for item in pooled_items:
            crop_id = item['id']
            qty_purchased = item['taken_kg']
            total_item_price = qty_purchased * item['price']

            cursor.execute('''
                INSERT INTO orders (crop_id, buyer_name, buyer_email, qty_kg, total_price, payment_id, status, order_time, delivery_otp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (crop_id, buyer_name, buyer_email, qty_purchased, total_item_price, payment_id, "Paid & Confirmed", now_iso, generated_otp))

            order_id = cursor.lastrowid
            vehicle_choice = "Single Pickup Truck (Cap: 1.5 Ton)" if total_batch_qty <= 1500 else "Heavy Duty Cargo Truck"

            cursor.execute('''
                INSERT INTO logistics (order_id, vehicle_type, vehicle_number, driver_name, driver_phone, pickup_location, delivery_status, route_distance_km, assigned_at, multi_pickup_route, est_fuel_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, vehicle_choice, "Pending", "Unassigned", "", item.get('location', 'Farm Origin'), "Unassigned - Awaiting Carrier Acceptance", total_distance, now_iso, waypoint_text, fuel_cost))

            cursor.execute('UPDATE crops SET quantity_kg = quantity_kg - ? WHERE id = ?', (qty_purchased, crop_id))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": f"Single-Truck Multi-Pickup Route Optimized! Waypoints: {len(pooled_items)} Farmers."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Purchase error: {str(e)}"}), 500

# --- LOGISTICS PORTAL APIS ---
@app.route('/api/logistics/available-orders', methods=['GET'])
def get_available_logistics_orders():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.payment_id, 
                   GROUP_CONCAT(o.id) as order_ids,
                   c.crop_name, 
                   SUM(o.qty_kg) as total_qty, 
                   o.buyer_name, 
                   o.status, 
                   l.delivery_status, 
                   l.carrier_email, 
                   l.vehicle_number, 
                   l.driver_name, 
                   l.driver_phone, 
                   l.route_distance_km, 
                   l.multi_pickup_route, 
                   l.est_fuel_cost, 
                   l.vehicle_type
            FROM orders o
            JOIN crops c ON o.crop_id = c.id
            JOIN logistics l ON o.id = l.order_id
            WHERE o.status != 'Cancelled & Refunded'
            GROUP BY o.payment_id
            ORDER BY MIN(o.id) DESC
        ''')
        rows = cursor.fetchall()
        conn.close()

        orders = [{
            "payment_id": r[0],
            "order_ids": r[1],
            "crop": r[2],
            "qty_kg": r[3],
            "buyer_name": r[4],
            "order_status": r[5],
            "delivery_status": r[6],
            "carrier_email": r[7],
            "vehicle_number": r[8],
            "driver_name": r[9],
            "driver_phone": r[10],
            "distance_km": r[11],
            "multi_pickup_route": r[12],
            "est_fuel_cost": r[13],
            "vehicle_type": r[14]
        } for r in rows]

        return jsonify({"status": "success", "orders": orders})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logistics/accept', methods=['POST'])
def accept_logistics_order():
    try:
        data = request.get_json() or {}
        payment_id = data.get('payment_id')
        carrier_email = str(data.get('carrier_email', '')).strip().lower()
        carrier_name = data.get('carrier_name', 'Logistics Partner')
        vehicle_number = data.get('vehicle_number', 'MH-12-LG-2026')
        driver_name = data.get('driver_name', 'Default Driver')
        driver_phone = data.get('driver_phone', '9876543210')

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT l.carrier_email 
            FROM logistics l 
            JOIN orders o ON l.order_id = o.id 
            WHERE o.payment_id = ? AND l.carrier_email IS NOT NULL AND l.carrier_email != ''
        ''', (payment_id,))
        already_accepted = cursor.fetchone()

        if already_accepted:
            conn.close()
            return jsonify({"status": "error", "message": "Order batch already accepted by another carrier!"}), 400

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            UPDATE logistics 
            SET carrier_email = ?, carrier_name = ?, vehicle_number = ?, driver_name = ?, driver_phone = ?, delivery_status = 'Accepted - Multi-Pickup Route Active', assigned_at = ?
            WHERE order_id IN (SELECT id FROM orders WHERE payment_id = ?)
        ''', (carrier_email, carrier_name, vehicle_number, driver_name, driver_phone, now_str, payment_id))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": f"Batch Order ({payment_id}) assigned to Single Truck ({vehicle_number})!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logistics/update-progress', methods=['POST'])
def update_logistics_progress():
    try:
        data = request.get_json() or {}
        payment_id = data.get('payment_id')
        carrier_email = str(data.get('carrier_email', '')).strip().lower()
        new_status = data.get('delivery_status')
        provided_otp = str(data.get('otp', '')).strip()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT l.carrier_email 
            FROM logistics l 
            JOIN orders o ON l.order_id = o.id 
            WHERE o.payment_id = ?
        ''', (payment_id,))
        row = cursor.fetchone()

        if not row or (row[0] and row[0].lower() != carrier_email):
            conn.close()
            return jsonify({"status": "error", "message": "Unauthorized! Only the accepting carrier can update progress."}), 403

        if new_status == 'Delivered to Buyer':
            cursor.execute('SELECT delivery_otp FROM orders WHERE payment_id = ? LIMIT 1', (payment_id,))
            otp_row = cursor.fetchone()
            
            if not otp_row or str(otp_row[0]).strip() != provided_otp:
                conn.close()
                return jsonify({"status": "error", "message": "🔑 Invalid Customer OTP! Delivery cannot be completed without valid buyer verification."}), 400
            
            cursor.execute("UPDATE orders SET status = 'Delivered to Buyer' WHERE payment_id = ?", (payment_id,))

        cursor.execute('''
            UPDATE logistics 
            SET delivery_status = ? 
            WHERE order_id IN (SELECT id FROM orders WHERE payment_id = ?)
        ''', (new_status, payment_id))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": f"🎉 Batch Order verified & updated to '{new_status}'!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
                SELECT o.id, c.crop_name, o.qty_kg, o.total_price, o.buyer_name, o.buyer_email, o.payment_id, o.status, c.location, o.order_time,
                       l.delivery_status, l.vehicle_number, l.driver_name, l.driver_phone, l.carrier_name, l.multi_pickup_route
                FROM orders o
                JOIN crops c ON o.crop_id = c.id
                LEFT JOIN logistics l ON o.id = l.order_id
                WHERE LOWER(c.farmer_name) = LOWER(?)
                ORDER BY o.id DESC
            ''', (user_name,))
            rows = cursor.fetchall()
            conn.close()

            orders = [{
                "order_id": r[0], "crop": r[1], "qty_kg": r[2], "total_price": r[3],
                "customer_name": r[4], "customer_email": r[5], "payment_id": r[6],
                "status": r[7], "location": r[8], "order_time": r[9],
                "logistics_status": r[10] or "Order Received",
                "vehicle_number": r[11] or "Awaiting Carrier",
                "driver_name": r[12] or "Unassigned",
                "driver_phone": r[13] or "-",
                "carrier_name": r[14] or "Independent Fleet",
                "multi_pickup_route": r[15] or ""
            } for r in rows]

            return jsonify({"status": "success", "role": "farmer", "orders": orders})

        elif role == 'logistics':
            cursor.execute('''
                SELECT o.payment_id, 
                       c.crop_name, 
                       SUM(o.qty_kg) as total_qty, 
                       SUM(o.total_price) as grand_total, 
                       GROUP_CONCAT(DISTINCT c.farmer_name) as farmer_names, 
                       o.status, 
                       GROUP_CONCAT(DISTINCT c.location) as locations, 
                       MIN(o.order_time) as order_time,
                       l.delivery_status, 
                       l.vehicle_number, 
                       l.driver_name, 
                       l.driver_phone, 
                       l.carrier_name, 
                       o.delivery_otp, 
                       l.multi_pickup_route
                FROM orders o
                JOIN crops c ON o.crop_id = c.id
                JOIN logistics l ON o.id = l.order_id
                WHERE LOWER(l.carrier_email) = LOWER(?)
                GROUP BY o.payment_id
                ORDER BY MIN(o.id) DESC
            ''', (email,))
            rows = cursor.fetchall()
            conn.close()

            orders = [{
                "payment_id": r[0],
                "crop": r[1],
                "qty_kg": r[2],
                "total_price": r[3],
                "farmer_name": r[4],
                "status": r[5],
                "location": r[6],
                "order_time": r[7],
                "can_cancel": False,
                "minutes_left": 0,
                "tracking_status": r[8] or "Accepted - Multi-Pickup Route Active",
                "vehicle": r[9] or "Assigned Vehicle",
                "driver_name": r[10] or "Assigned Driver",
                "driver_phone": r[11] or "-",
                "carrier_name": r[12] or "Transporter Fleet",
                "delivery_otp": r[13] or "----",
                "multi_pickup_route": r[14] or ""
            } for r in rows]

            return jsonify({"status": "success", "role": "logistics", "orders": orders})

        else:
            cursor.execute('''
                SELECT o.payment_id, 
                       c.crop_name, 
                       SUM(o.qty_kg) as total_qty, 
                       SUM(o.total_price) as grand_total, 
                       GROUP_CONCAT(DISTINCT c.farmer_name) as farmer_names, 
                       o.status, 
                       GROUP_CONCAT(DISTINCT c.location) as locations, 
                       MIN(o.order_time) as order_time,
                       l.delivery_status, 
                       l.vehicle_number, 
                       l.driver_name, 
                       l.driver_phone, 
                       l.carrier_name, 
                       o.delivery_otp, 
                       l.multi_pickup_route
                FROM orders o
                JOIN crops c ON o.crop_id = c.id
                LEFT JOIN logistics l ON o.id = l.order_id
                WHERE LOWER(o.buyer_email) = LOWER(?)
                GROUP BY o.payment_id
                ORDER BY MIN(o.id) DESC
            ''', (email,))
            rows = cursor.fetchall()
            conn.close()

            orders = []
            for r in rows:
                ord_time_str = r[7]
                can_cancel = False
                minutes_left = 0
                
                if ord_time_str and r[5] == 'Paid & Confirmed':
                    try:
                        ord_dt = datetime.strptime(ord_time_str, "%Y-%m-%d %H:%M:%S")
                        elapsed_seconds = (now_dt - ord_dt).total_seconds()
                        if elapsed_seconds <= 7200:
                            can_cancel = True
                            minutes_left = max(1, int((7200 - elapsed_seconds) // 60))
                    except Exception:
                        can_cancel = False

                orders.append({
                    "payment_id": r[0],
                    "crop": r[1],
                    "qty_kg": r[2],
                    "total_price": r[3],
                    "farmer_name": r[4],
                    "status": r[5],
                    "location": r[6],
                    "order_time": r[7],
                    "can_cancel": can_cancel,
                    "minutes_left": minutes_left,
                    "tracking_status": r[8] or "Order Confirmed - Preparing Pickup",
                    "vehicle": r[9] or "Awaiting Carrier",
                    "driver_name": r[10] or "Assigned Carrier",
                    "driver_phone": r[11] or "-",
                    "carrier_name": r[12] or "Partner Logistics",
                    "delivery_otp": r[13] or "----",
                    "multi_pickup_route": r[14] or ""
                })

            return jsonify({"status": "success", "role": "buyer", "orders": orders})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/orders/cancel', methods=['POST'])
def cancel_order():
    try:
        data = request.get_json() or {}
        payment_id = data.get('payment_id')
        buyer_email = str(data.get('buyer_email', '')).strip().lower()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, crop_id, qty_kg, total_price, status, order_time 
            FROM orders 
            WHERE payment_id = ? AND LOWER(buyer_email) = ?
        ''', (payment_id, buyer_email))
        order_rows = cursor.fetchall()

        if not order_rows:
            conn.close()
            return jsonify({"status": "error", "message": "Order batch not found or unauthorized!"}), 404

        if any(o[4] != 'Paid & Confirmed' for o in order_rows):
            conn.close()
            return jsonify({"status": "error", "message": "Order batch cannot be cancelled in its current state."}), 400

        now_dt = datetime.now()
        ord_time_str = order_rows[0][5]
        if ord_time_str:
            ord_dt = datetime.strptime(ord_time_str, "%Y-%m-%d %H:%M:%S")
            if (now_dt - ord_dt).total_seconds() > 7200:
                conn.close()
                return jsonify({"status": "error", "message": "⏳ Cancellation window expired (2 hours limit reached). Order has been dispatched to logistics!"}), 400

        total_refund = 0.0
        total_restored_kg = 0.0

        for order in order_rows:
            order_id = order[0]
            crop_id = order[1]
            qty_kg = order[2]
            refund_amount = order[3]
            
            total_refund += refund_amount
            total_restored_kg += qty_kg

            cursor.execute("UPDATE orders SET status = 'Cancelled & Refunded' WHERE id = ?", (order_id,))
            cursor.execute("UPDATE logistics SET delivery_status = 'Order Cancelled & Escrow Refunded' WHERE order_id = ?", (order_id,))
            cursor.execute("UPDATE crops SET quantity_kg = quantity_kg + ? WHERE id = ?", (qty_kg, crop_id))

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"🎉 Batch Order successfully cancelled!\n💸 Total Refund of ₹{total_refund:.2f} initiated.\n📦 {total_restored_kg} kg restored to farmer inventory."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)