# topics.py

TOPIC_HUBS = {
    "Engineering": [
        "Biomedical Engineering",
        "Electrical Engineering",
        "Mechanical Engineering",
        "Automotive Engineering",
        "Software Engineering",
    ],
    "Future Tech": [
        "Artificial Intelligence",
        "Bionics",
        "Brain Computer Interface",
        "Nuclear Fusion",
        "Robotics",
        "Nuclear Fission",
        "Cybersecurity",
        "Quantum Computing",
    ],
    "Life Sciences": [
        "Biology",
        "Molecular Biology",
        "Neuroscience",
        "Biochemistry",
        "Biotechnology",
    ],
    "Hard Sciences": [
        "Physics",
        "Chemistry",
        "Data Science",
        "Material Science",
    ]
}

# Flattened list for the "Scout" script to iterate through
ALL_TOPICS = [topic for group in TOPIC_HUBS.values() for topic in group]
