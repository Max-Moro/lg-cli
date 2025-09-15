"""Module for testing import optimization."""

# Standard library imports (external)
import os
import sys
import json
import re
import datetime
import pathlib
from typing import List, Dict, Optional, Union, Any
from collections import defaultdict, Counter
from itertools import chain, combinations
from functools import reduce, partial

# Third-party imports (external)
import numpy as np
import pandas as pd
import requests
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String
from pydantic import BaseModel, Field, validator

# Local/relative imports (should be considered local)
# … 12 imports omitted

# Mixed import styles
import sqlite3, pickle, csv
from datetime import datetime, timedelta, timezone

# Import with alias
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.model_selection import train_test_split as tts
# … import omitted

# Conditional imports
try:
    import uvloop
except ImportError:
    uvloop = None

# Long from-import lists (candidates for summarization)
from django.http import (
    HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect,
    HttpResponsePermanentRedirect, HttpResponseNotModified,
    HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden,
    HttpResponseNotAllowed, HttpResponseGone, HttpResponseServerError
)

from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
    throttle_classes, parser_classes, renderer_classes
)

# … 11 imports omitted

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
