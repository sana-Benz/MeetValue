# MeetValue — Project Structure

meetcost/
├── README.md
├── .gitignore
├── backend/
│   ├── functions/
│   │   ├── calculate_cost/
│   │   │   └── handler.py
│   │   └── get_recommendations/
│   │       └── handler.py
│   ├── shared/
│   │   └── bedrock_client.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── infrastructure/
│   └── template.yaml
└── docs/
    └── architecture.md

## Conventions
- Each Lambda function lives in its own folder under backend/functions/
- Shared logic (e.g. Bedrock client) goes in backend/shared/, imported by functions, never duplicated
- Frontend has no build step — plain files served directly
- All AWS resource names in infrastructure/template.yaml must be prefixed with `meetcost-`
