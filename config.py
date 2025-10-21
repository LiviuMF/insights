import os

from dotenv import load_dotenv


load_dotenv()


API_URL = os.environ.get('API_URL')
TEMP_REASONS = ['fara abatere', 'usa deschisa', 'defectiune tehnica', 'pana curent']
TEMP_ACTIONS = ['fara actiune', 'usa inchisa', 'defectiune remediata', 'platit factura']

COOLING_MAPPER = {
    'refrigerare (carne / organe)': [0,3],
    'refrigerare (mezeluri / lactate)': [0,5],
    'refrigerare (fructe / legume)': [0,7],
    'congelare': [-18,-18]
}
