# ggprofit

## Overview

This project is a web application for tracking your performance in poker tournaments. It is built using Streamlit and Python.

---

## Environment Setup

### Required Software

- Python 3.x
- pip (Python package manager)

### Step-by-step Setup

1. **Clone the repository:**
	```
    git clone git@github.com:mura5726/ggprofit.git
	```

2. **Navigate to the project directory:**
	```
    cd ggprofit
	```

3. **Install the required packages:**
	```
    pip install -r requirements.txt
	```

4. **Download txt from game craft and place it in the tournaments folder:**
	```
	mkdir tournaments
	```

5. **Run the Streamlit app:**
	```
    streamlit run app.py
	```
    
---

## Folder Structure

```
poker-tournament-profit-tracker/
│
├── app.py                      # Main Streamlit application file
├── requirements.txt            # Project dependencies
│
├── tournaments/                # Folder containing tournament text files
│   ├── tournament_1.txt
│   ├── tournament_2.txt
│   └── ...
│
├── out.csv                     # Output file
└── README.md                   # Documentation

```

---

## Usage

After running the Streamlit app, navigate to `http://localhost:8501` in your web browser. Use the filters provided to analyze your tournament data.

---

## Contributing

If you would like to contribute, please fork the repository and create a pull request, or open an issue for discussion.

---

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

