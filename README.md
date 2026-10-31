# CitiSevik

### A prototype for better urban infrastructure coordination

**Live Demo:** [Explore CitiSevik](https://citisevik-deployment.onrender.com/)

CitiSevik is a prototype platform that explores how cities can coordinate civic complaints, infrastructure work and environmental concerns more effectively.

In a city, different departments often work on issues that are connected to one another. A road repair, a drainage complaint and an ongoing infrastructure project may all affect the same area. When these activities are considered separately, it can lead to repeated work, unnecessary disruption and inefficient use of resources.

CitiSevik brings these different pieces of information into one place to help make those connections easier to identify.

## Dashboard Preview
<img width="1365" height="607" alt="image" src="https://github.com/user-attachments/assets/4417afdd-92f7-4344-a313-56a15c471153" />
<img width="1091" height="580" alt="image" src="https://github.com/user-attachments/assets/2c57848a-3359-41c2-adb3-bab2343ebf29" />
<img width="1366" height="599" alt="image" src="https://github.com/user-attachments/assets/1b0db338-b747-48df-9f6d-e2e576ee609b" />



## What does it do?

The prototype brings together four main areas:

- **Civic complaints:** View reported urban issues and understand their location and context.
- **Infrastructure projects:** Explore ongoing or proposed infrastructure work.
- **Environmental context:** Consider local environmental risks while assessing urban issues.
- **Municipal coordination:** Suggest relevant departments, possible actions and verification steps based on the available information.

It also includes a planning component that explores how different infrastructure interventions can be compared using estimated costs, potential benefits and local conditions.

## Exploring the demo

The easiest way to understand CitiSevik is to explore it as a municipal planning and coordination tool.

1. **Explore the urban information:** Look through the available civic issues, infrastructure projects and environmental context.
2. **Understand the connections:** See how issues in the same area may overlap with existing projects or other urban concerns.
3. **Review suggested responses:** Explore recommendations for responsible departments, coordinated actions and verification.
4. **Compare interventions:** Consider different infrastructure approaches using the planning information available in the prototype.

**Try it here:** [https://citisevik-deployment.onrender.com/](https://citisevik-deployment.onrender.com/)

## How it is built

CitiSevik uses:

- **Python and FastAPI** for the backend.
- **HTML, CSS and JavaScript** for the frontend.
- **JSON-based demo data** to represent civic and infrastructure information.

## Running locally

Clone the repository:

```bash
git clone https://github.com/asiyaghk-bot/citisevik-deployment.git
cd citisevik-deployment
```

Move into the application directory:

```bash
cd app
```

Install the dependencies:

```bash
pip install -r backend/requirements.txt
```

Start the application:

```bash
uvicorn backend.main:app --reload
```

## Scope and limitations

CitiSevik is currently a working prototype built to demonstrate the concept and its proposed workflow.

The information shown in the demo is illustrative and uses demo data. The platform is not connected to live municipal databases, official complaint systems or municipal departments. Its recommendations are intended to support human decision-making rather than replace it.

## The idea behind CitiSevik

Cities don't just need more infrastructure. They also need better ways to plan, coordinate and maintain what they already have.

CitiSevik is an exploration of what that coordination could look like.
- No live BMC/NMMC integration, real notifications, field inspection, verified utility GIS, calibrated flood/traffic models or production deployment.
- Global case studies are reference examples, not automatic recommendations; local feasibility still needs engineering review.

## Reset demo data

Stop the server and delete `app/backend/citisevik.sqlite3`. It will be recreated and reseeded at next launch.
