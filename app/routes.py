from fastapi import APIRouter, Query, HTTPException
from typing import List
from pydantic import Field
from app.schemas.bodies.earth import Earth
from app.schemas.orbits.orbit_base import OrbitBase, OrbitInput
from app.schemas.trajectory_base import Trajectory
from app.schemas.transfer_type import TransferInput
from utils.hohmann.hohmann_transfer import HohmannTransfer
from logger_handler import handle_logger
from utils.loader import ORBIT_DIR, TRAJECTORY_DIR, load_orbit_by_id, load_orbits, load_trajectories, load_trajectory_by_id
from utils.paginate import PaginatedResponse

logger = handle_logger()

# Initialize router
router = APIRouter()


@router.post("/orbit", response_model=dict, status_code=200)
async def create_orbit(input: OrbitInput):
    #TODO: Remove the default Earth
    """
    Create a new orbit and store it in the specified format.

    Args:
        altitude_perigee (float): Altitude of the perigee in km.
        altitude_apogee (float): Altitude of the apogee in km.
        inclination (float): Orbital inclination in degrees.
        file_type (str, optional): File format to store the orbit (json, csv, xml). Defaults to "json".

    Returns:
        dict: Success message and orbit details.

    Response Schema:
    {
        "message": "Orbit created successfully",
        "orbit": {
            "id": int,
            "name": str,
            "altitude_perigee": float,
            "altitude_apogee": float,
            "inclination": float,
            "raan": float,
            "argp": float,
            "nu": float
        }
    }

    Example (cURL):
        ```bash
        curl -X POST "http://localhost:8000/orbit" \
            -H "Content-Type: application/json" \
            -d '{"altitude_perigee": 200, "altitude_apogee": 400, "inclination": 28.5}'
        ```

    Example (Python):
        ```python
        import requests

        response = requests.post(
            "http://localhost:8000/orbit",
            json={"altitude_perigee": 200, "altitude_apogee": 400, "inclination": 28.5}
        )
        print(response.json())
        ```

    Example (JavaScript):
        ```javascript
        fetch("http://localhost:8000/orbit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ "altitude_perigee": 200, "altitude_apogee": 400, "inclination": 28.5 })
        })
        .then(response => response.json())
        .then(data => console.log(data));
        ```
    """
    
    try:
        orbit = OrbitBase(input.altitude_perigee, input.altitude_apogee, input.inclination, input.raan, input.argp,input.nu, central_body=Earth()) # default Earth for now

        file_path = ORBIT_DIR / input.file_type / f"{orbit.id}.{input.file_type}"

        if input.file_type == "json":
            orbit.to_json(filename=str(file_path))
        elif input.file_type == "csv":
            orbit.to_csv(filename=str(file_path))
        elif input.file_type == "xml":
            orbit.to_xml(filename=str(file_path))
        else:
            raise ValueError("Invalid file type specified.")

        return {"message": "Orbit created successfully", "orbit": orbit.to_json()}
    except ValueError as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500)


@router.get("/orbit/{id}", response_model=dict, status_code=200)
async def get_orbit(
    id: str = int(
        ..., 
        description="Unique identifier of the orbit.",
        pattern="^\d+$"
    ),
    file_type: str = Query(
        None,
        description="File format to search for (json, csv, xml). Defaults to None.",
        pattern="^(json|csv|xml)$"
    )
):
    """
    Retrieve an orbit by its ID and optional file type.

    Args:
        id (str): Unique identifier of the orbit.
        file_type (str, optional): File format to search for (json, csv, xml). Defaults to None.

    Returns:
        dict: Details of the requested orbit.
    
    Response Schema:
    {
        "orbit": {
            "id": int,
            "name": str,
            "altitude_perigee": float,
            "altitude_apogee": float,
            "inclination": float,
            "raan": float,
            "argp": float,
            "nu": float
        }
    }

    Example (cURL):
        ```bash
        curl -X GET "http://localhost:8000/orbits/123456" \
            -H "Content-Type: application/json"
        ```

    Example (Python):
        ```python
        import requests

        response = requests.get("http://localhost:8000/orbits/123456")
        print(response.json())
        ```

    Example (JavaScript):
        ```javascript
        fetch("http://localhost:8000/orbits/123456")
        .then(response => response.json())
        .then(data => console.log(data));
        ```
    """
    
    try:
        orbit = await load_orbit_by_id(id, file_type)
        return {"orbit": orbit.to_json()}
    except FileNotFoundError as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500)


@router.get("/trajectory/{id}", response_model=dict, status_code=200)
async def get_trajectory(
    id: str = int(
        ..., 
        description="Unique identifier of the trajectory.",
        pattern="^\d+$"
    ),
    file_type: str = Query(
        None,
        description="File format to search for (json, csv, xml). Defaults to None.",
        pattern="^(json|csv|xml)$"
    )
):
    """
    Retrieve a trajectory by its ID and optional file type.

    Args:
        id (str): Unique identifier of the trajectory.
        file_type (str, optional): File format to search for (json, csv, xml). Defaults to None.

    Returns:
        dict: Details of the requested trajectory.

    Response Schema:
    {
        "trajectory": {
            "id": int,
            "delta_v1": float,
            "delta_v2": float,
            "time_of_flight": float,
            "initial_orbit_id": int,
            "target_orbit_id": int,
            "points": [
                {
                    "time": str,
                    "position": [float, float, float],
                    "velocity": [float, float, float]
                },
                ...
            ],
            "transfer_type_id": int,
            "name": str
        }
    }

    Example (cURL):
        ```bash
        curl -X GET "http://localhost:8000/trajectories/123456" \
            -H "Content-Type: application/json"
        ```

    Example (Python):
        ```python
        import requests

        response = requests.get("http://localhost:8000/trajectories/123456")
        print(response.json())
        ```

    Example (JavaScript):
        ```javascript
        fetch("http://localhost:8000/trajectories/123456")
        .then(response => response.json())
        .then(data => console.log(data));
        ```
    """
    
    try:
        trajectory = await load_trajectory_by_id(id, file_type)
        return {"trajectory": trajectory.to_json()}
    except FileNotFoundError as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500)


@router.post("/transfers", response_model=dict, status_code=200)
async def perform_transfer_calculation(input: TransferInput):
    """
    Calculate an orbital transfer between two orbits and store the trajectory.

    Args:
        initial_orbit_id (int): Index of the initial orbit in the stored list.
        target_orbit_id (int): Index of the target orbit in the stored list.
        transfer_type (str): Type of orbital transfer (e.g., "hohmann"). Defaults to "hohmann".
        file_type (str): File format to store the trajectory (json, csv, xml). Defaults to "json".

    Returns:
        dict: Success message and trajectory details.

    Response Schema:
    {
        "message": "Transfer calculated successfully",
        "trajectory": {
            "id": int,
            "delta_v1": float,
            "delta_v2": float,
            "time_of_flight": float,
            "initial_orbit_id": int,
            "target_orbit_id": int,
            "points": [
                {
                    "time": str,
                    "position": [float, float, float],
                    "velocity": [float, float, float]
                },
                ...
            ],
            "transfer_type_id": int,
            "name": str
        }
    }

    Example (cURL):
        ```bash
        curl -X POST "http://localhost:8000/transfers" \
            -H "Content-Type: application/json" \
            -d '{"initial_orbit_id": 0, "target_orbit_id": 1, "transfer_type": "hohmann"}'
        ```

    Example (Python):
        ```python
        import requests

        response = requests.post(
            "http://localhost:8000/transfers",
            json={"initial_orbit_id": 0, "target_orbit_id": 1, "transfer_type": "hohmann"}
        )
        print(response.json())
        ```

    Example (JavaScript):
        ```javascript
        fetch("http://localhost:8000/transfers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ "initial_orbit_id": 0, "target_orbit_id": 1, "transfer_type": "hohmann" })
        })
        .then(response => response.json())
        .then(data => console.log(data));
        ```
    """
    
    try:

        initial_orbit = await load_orbit_by_id(input.initial_orbit_id)
        target_orbit = await load_orbit_by_id(input.target_orbit_id)

        if input.transfer_type == "hohmann":
            calculator = HohmannTransfer()
        else:
            raise ValueError(f"Transfer type '{input.transfer_type}' not supported")

        trajectory = calculator.calculate_transfer(initial_orbit, target_orbit)
        file_path = TRAJECTORY_DIR / input.file_type / f"{trajectory.id}.{input.file_type}"

        if input.file_type == "json":
            trajectory.to_json(filename=str(file_path))
        elif input.file_type == "csv":
            trajectory.to_csv(filename=str(file_path))
        elif input.file_type == "xml":
            trajectory.to_xml(filename=str(file_path))
        else:
            raise ValueError("Invalid file type specified.")

        return {"message": "Transfer calculated successfully", "trajectory": trajectory.to_json()}
    except ValueError as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500)
    
@router.get("/orbits", response_model=PaginatedResponse, status_code=200)
async def get_orbits(
        file_type: str = Query(
            None,
            description="File format to search for (json, csv, xml). Defaults to None.",
        pattern="^(json|csv|xml)$"
        ),
        page: int = Field(
            1,
            ge=1,
            description="The current page number, starting from 1."
        ),
        page_size: int = Field(
            50,
            ge=1,
            le=100,
            description="The number of items per page. Must be between 1 and 100."
        )
    ):
    """
    Retrieve all stored orbits in the specified format with pagination.

    Args:
        file_type (str, optional): File format to search for (json, csv, xml). Defaults to "json".
        page (int, optional): Page number (1-based). Defaults to 1.
        page_size (int, optional): Number of items per page. Defaults to 50.

    Returns:
        dict: Paginated list of orbits and metadata.

    Response Schema:
    {
        "page": int,
        "page_size": int,
        "total_items": int,
        "total_pages": int,
        "next": str | null,
        "data": [
            {
                "id": int,
                "name": str,
                "altitude_perigee": float,
                "altitude_apogee": float,
                "inclination": float,
                "raan": float,
                "argp": float,
                "nu": float
            },
            ...
        ]
    }

    Example (cURL):
        ```bash
        curl -X GET "http://localhost:8000/orbits?page=1&page_size=20" \
            -H "Content-Type: application/json"
        ```

    Example (Python):
        ```python
        import requests

        response = requests.get("http://localhost:8000/orbits", params={"page": 1, "page_size": 20})
        print(response.json())
        ```

    Example (JavaScript):
        ```javascript
        fetch("http://localhost:8000/orbits?page=1&page_size=20")
        .then(response => response.json())
        .then(data => console.log(data));
        ```
    """
    
    try:
        orbits: List[OrbitBase] = await load_orbits(file_type)
        base_url = "/orbits"
        return PaginatedResponse.paginate_items([orbit.to_json() for orbit in orbits], base_url, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500)


@router.get("/trajectories", response_model=PaginatedResponse, status_code=200)
async def get_trajectories(
        file_type: str = Query(
            None,
            description="File format to search for (json, csv, xml). Defaults to None.",
        pattern="^(json|csv|xml)$"
        ),
        page: int = Field(
            1,
            ge=1,
            description="The current page number, starting from 1."
        ),
        page_size: int = Field(
            50,
            ge=1,
            le=100,
            description="The number of items per page. Must be between 1 and 100."
        )
    ):
    """
    Retrieve all stored trajectories in the specified format with pagination.

    Args:
        file_type (str, optional): File format to search for (json, csv, xml). Defaults to "json".
        page (int, optional): Page number (1-based). Defaults to 1.
        page_size (int, optional): Number of items per page. Defaults to 50.

    Returns:
        dict: Paginated list of trajectories and metadata.

    Response Schema:
    {
        "page": int,
        "page_size": int,
        "total_items": int,
        "total_pages": int,
        "next": str | null,
        "data": [
            {
                "id": int,
                "delta_v1": float,
                "delta_v2": float,
                "time_of_flight": float,
                "initial_orbit_id": int,
                "target_orbit_id": int,
                "points": [
                    {
                        "time": str,
                        "position": [float, float, float],
                        "velocity": [float, float, float]
                    },
                    ...
                ],
                "transfer_type_id": int,
                "name": str
            },
            ...
        ]
    }

    Example (cURL):
        ```bash
        curl -X GET "http://localhost:8000/trajectories?page=1&page_size=20" \
            -H "Content-Type: application/json"
        ```

    Example (Python):
        ```python
        import requests

        response = requests.get("http://localhost:8000/trajectories", params={"page": 1, "page_size": 20})
        print(response.json())
        ```

    Example (JavaScript):
        ```javascript
        fetch("http://localhost:8000/trajectories?page=1&page_size=20")
        .then(response => response.json())
        .then(data => console.log(data));
        ```
    """
    
    try:
        trajectories: List[Trajectory] = await load_trajectories(file_type)
        base_url = "/trajectories"
        return PaginatedResponse.paginate_items([trajectory.to_json() for trajectory in trajectories], base_url, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500)
