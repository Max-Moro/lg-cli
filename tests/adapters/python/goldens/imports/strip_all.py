"""Module for testing import optimization."""

# Standard library imports (external)
# … 17 imports omitted

# Third-party imports (external)
# … 13 imports omitted

# Local/relative imports (should be considered local)
# … 12 imports omitted

# Mixed import styles
# … 6 imports omitted

# Import with alias
# … 4 imports omitted

# Conditional imports
try:
    # … import omitted
except ImportError:
    uvloop = None

# Long from-import lists (candidates for summarization)
# … 29 imports omitted

class ImportTestClass:
    """Class that uses imported modules."""
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.df = pd.DataFrame()
        self.model = User()
    
    def process_data(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Process data using imported libraries."""
        df = pd.DataFrame(data)
        return df.fillna(0)
    
    def make_request(self, url: str) -> Optional[Dict]:
        """Make HTTP request using requests library."""
        try:
            response = requests.get(url, timeout=30)
            return response.json()
        except requests.RequestException:
            return None

def use_imports():
    """Function demonstrating import usage."""
    # Use standard library
    current_time = datetime.now()
    file_path = pathlib.Path("test.txt")
    
    # Use third-party libraries
    data = np.array([1, 2, 3, 4, 5])
    df = pd.DataFrame({"values": data})
    
    # Use local imports
    processor = DataProcessor()
    user = User(name="test")
    
    return current_time, df, user
