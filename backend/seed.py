import datetime
from app.database import engine, Base, SessionLocal
from app.models.sensor import SensorConfig, HistoricalOrder

def seed():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if configurations exist, if not, add some
        if db.query(SensorConfig).count() == 0:
            configs = [
                SensorConfig(part_number="PCA 1.2005.10S 10", resistance=100, sensor_type="T-type", has_nt_step=True),
                SensorConfig(part_number="PCA 1.2005.50S 50", resistance=500, sensor_type="E-type", has_nt_step=False),
                SensorConfig(part_number="PCA 1.2005.100S 100", resistance=1000, sensor_type="H-type", has_nt_step=True),
                SensorConfig(part_number="PCA 2.3005.10S 10", resistance=100, sensor_type="E-type", has_nt_step=True),
                SensorConfig(part_number="PCA 2.3005.100S 100", resistance=1000, sensor_type="T-type", has_nt_step=False),
            ]
            db.add_all(configs)
            print("Seeded 5 sensor configurations.")

        # Check if historical orders exist, if not, add some
        if db.query(HistoricalOrder).count() == 0:
            # We seed some historical values for viscosities and air humidity.
            # Averages will be calculated from these values:
            # ds1_viscosity: average is (12.4 + 12.8 + 11.9 + 12.2 + 12.5) / 5 = 12.36 Pa.s
            # ds2_viscosity: average is (14.1 + 13.9 + 14.3 + 13.8 + 14.0) / 5 = 14.02 Pa.s
            # air_humidity: average is (42.5 + 45.0 + 46.2 + 44.1 + 43.8) / 5 = 44.32 %
            orders = [
                HistoricalOrder(
                    order_number="ORD-001",
                    paste_lot_ds1="LOT-DS1-A",
                    paste_lot_ds2="LOT-DS2-X",
                    ds1_viscosity=12.4,
                    ds2_viscosity=14.1,
                    air_humidity=42.5,
                    timestamp=datetime.datetime.now() - datetime.timedelta(days=10)
                ),
                HistoricalOrder(
                    order_number="ORD-002",
                    paste_lot_ds1="LOT-DS1-A",
                    paste_lot_ds2="LOT-DS2-Y",
                    ds1_viscosity=12.8,
                    ds2_viscosity=13.9,
                    air_humidity=45.0,
                    timestamp=datetime.datetime.now() - datetime.timedelta(days=8)
                ),
                HistoricalOrder(
                    order_number="ORD-003",
                    paste_lot_ds1="LOT-DS1-B",
                    paste_lot_ds2="LOT-DS2-X",
                    ds1_viscosity=11.9,
                    ds2_viscosity=14.3,
                    air_humidity=46.2,
                    timestamp=datetime.datetime.now() - datetime.timedelta(days=5)
                ),
                HistoricalOrder(
                    order_number="ORD-004",
                    paste_lot_ds1="LOT-DS1-B",
                    paste_lot_ds2="LOT-DS2-Z",
                    ds1_viscosity=12.2,
                    ds2_viscosity=13.8,
                    air_humidity=44.1,
                    timestamp=datetime.datetime.now() - datetime.timedelta(days=2)
                ),
                HistoricalOrder(
                    order_number="ORD-005",
                    paste_lot_ds1="LOT-DS1-C",
                    paste_lot_ds2="LOT-DS2-Y",
                    ds1_viscosity=12.5,
                    ds2_viscosity=14.0,
                    air_humidity=43.8,
                    timestamp=datetime.datetime.now() - datetime.timedelta(days=1)
                ),
            ]
            db.add_all(orders)
            print("Seeded 5 historical orders for defaults calculation.")
            
        db.commit()
        print("Database seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
