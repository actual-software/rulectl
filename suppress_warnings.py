import warnings
import re

# Suppress the specific pkg_resources warning
warnings.filterwarnings(
    "ignore",
    message=re.escape("pkg_resources is deprecated as an API"),
    category=UserWarning
) 