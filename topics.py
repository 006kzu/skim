# topics.py

TOPIC_HUBS = {
    "Engineering & Systems": [
        "Biomedical Engineering",
        "Electrical Engineering",
        "Mechanical Engineering",
        "Automotive Engineering",
        "Software Engineering",
        "Robotics",
        "Power Electronics",
        "Civil Engineering",
    ],
    "Computing & Software": [
        "Artificial Intelligence",
        "Data Science",
        "Cybersecurity",
        "Quantum Computing",
        "Brain Computer Interface",
        "Bioinformatics",
    ],
    "Life Sciences": [
        "Biology",
        "Neuroscience",
        "Biotechnology",
        "Biochemistry",
        "Molecular Biology",
        "Bionics",
        "Medicine",
        "Cardiovascular Medicine",
        "Oncology",
        "Nanomedicine",
    ],
    "Physical Sciences": [
        "Physics",
        "Chemistry",
        "Material Science",
        "Nuclear Fusion",
        "Nuclear Fission",
        "Nuclear Physics",
        "Astronomy",
        "Environmental Science",
        "Climatology",
        "Energy",
    ]
}

# Flattened list for the "Scout" script to iterate through
ALL_TOPICS = list(
    set([topic for group in TOPIC_HUBS.values() for topic in group]))
