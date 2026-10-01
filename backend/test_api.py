import subprocess
import time
import urllib.request
import urllib.parse
import json
import sys

def run_tests():
    # Start the FastAPI server using the venv's python to run uvicorn
    print("Starting FastAPI server...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for the server to boot up
    time.sleep(6)
    
    success = True
    try:
        # Test 1: Health check
        print("\n--- Test 1: Health Check ---")
        req = urllib.request.Request("http://127.0.0.1:8000/health")
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            print(f"Response: {res_body}")
            res_json = json.loads(res_body)
            assert res_json["status"] == "ok"
            print("Health Check: SUCCESS")

        # Test 2: Get part numbers
        print("\n--- Test 2: Get Part Numbers ---")
        req = urllib.request.Request("http://127.0.0.1:8000/api/config/parts")
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            print(f"Parts list: {res_body}")
            parts = json.loads(res_body)
            assert "PCA 1.2005.10S 10" in parts
            print("Get Part Numbers: SUCCESS")

        # Test 3: Get part details
        print("\n--- Test 3: Get Part Details ---")
        part_num = urllib.parse.quote("PCA 1.2005.10S 10")
        req = urllib.request.Request(f"http://127.0.0.1:8000/api/config/details/{part_num}")
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            print(f"Part details: {res_body}")
            details = json.loads(res_body)
            assert details["resistance"] == 100
            assert details["sensor_type"] == "T-type"
            assert details["has_nt_step"] is True
            print("Get Part Details: SUCCESS")

        # Test 4: Calculate prediction with FULL inputs
        print("\n--- Test 4: Calculate Prediction (Full Inputs) ---")
        payload_full = {
            "part_number": "PCA 1.2005.10S 10",
            "resistance": 100,
            "sensor_type": "T-type",
            "has_nt_step": True,
            "sputter_machine": "Senvac",
            "film_thickness": 15.0,
            "sheet_resistance": 4.5,
            "tcr_sputter": 3.2,
            "substrate_batch": "BATCH-1",
            "pt_r20_value": 102.5,
            "paste_lot_ds1": "LOT-DS1-A",
            "paste_lot_ds2": "LOT-DS2-X",
            "ds1_viscosity": 12.0,
            "ds2_viscosity": 14.5,
            "air_humidity": 40.0
        }
        data = json.dumps(payload_full).encode('utf-8')
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/prediction/calculate",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            print(f"Prediction result (Full): {res_body}")
            res_json = json.loads(res_body)
            assert res_json["effective_ds1_viscosity"] == 12.0
            assert res_json["effective_ds2_viscosity"] == 14.5
            assert res_json["effective_air_humidity"] == 40.0
            assert "recommended_nc_value" in res_json
            assert isinstance(res_json["model_version"], str) and len(res_json["model_version"]) > 0
            assert res_json["is_ai_generated"] is True
            assert "compliance_disclaimer" in res_json
            print(f"NC Recommendation: {res_json['recommended_nc_value']}")
            print(f"Model Version: {res_json['model_version']}")
            print("Calculate Prediction (Full): SUCCESS")

        # Test 5: Calculate prediction with OMITTED screen printing inputs
        # Expected fallback values from database: ds1=12.36, ds2=14.02, humidity=44.32
        print("\n--- Test 5: Calculate Prediction (Omitted Inputs) ---")
        payload_omitted = {
            "part_number": "PCA 1.2005.10S 10",
            "resistance": 100,
            "sensor_type": "T-type",
            "has_nt_step": True,
            "sputter_machine": "FHR",
            "film_thickness": 16.2,
            "sheet_resistance": 4.8,
            "tcr_sputter": 3.0,
            "substrate_batch": "BATCH-2",
            "pt_r20_value": 101.8
        }
        data = json.dumps(payload_omitted).encode('utf-8')
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/prediction/calculate",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            print(f"Prediction result (Omitted/Fallback): {res_body}")
            res_json = json.loads(res_body)
            # The database seeded values have averages:
            # ds1_viscosity: 12.36, ds2_viscosity: 14.02, air_humidity: 44.32
            assert abs(res_json["effective_ds1_viscosity"] - 12.36) < 0.01
            assert abs(res_json["effective_ds2_viscosity"] - 14.02) < 0.01
            assert abs(res_json["effective_air_humidity"] - 44.32) < 0.01
            assert "recommended_nc_value" in res_json
            assert isinstance(res_json["model_version"], str) and len(res_json["model_version"]) > 0
            assert res_json["is_ai_generated"] is True
            assert "compliance_disclaimer" in res_json
            print(f"NC Recommendation: {res_json['recommended_nc_value']}")
            print(f"Model Version: {res_json['model_version']}")
            print("Calculate Prediction (Omitted): SUCCESS")

        # Test 6: Verify prediction history logs
        print("\n--- Test 6: Verify Prediction History ---")
        req = urllib.request.Request("http://127.0.0.1:8000/api/prediction/history")
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            history = json.loads(res_body)
            print(f"History list size: {len(history)}")
            assert len(history) >= 2
            print("Verify Prediction History: SUCCESS")

        # Test 7: Clear prediction history
        print("\n--- Test 7: Clear Prediction History ---")
        req = urllib.request.Request("http://127.0.0.1:8000/api/prediction/history", method="DELETE")
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            print(f"Clear history response: {res_body}")
            res_json = json.loads(res_body)
            assert res_json["status"] == "ok"
            print("Clear Prediction History: SUCCESS")


    except Exception as e:
        print(f"\nTEST FAILURE: {e}")
        success = False
    finally:
        print("\nStopping FastAPI server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Killing server process forcefully...")
            server_process.kill()
        print("Server stopped.")
        
    if success:
        print("\nALL TESTS COMPLETED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
