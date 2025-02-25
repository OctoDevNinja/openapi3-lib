from __future__ import annotations

import errno
from typing import Optional

import starlette.status
from fastapi import FastAPI, APIRouter, Body, Response, Path
from fastapi.responses import JSONResponse

from .schema import Pets, Pet, PetCreate, Error


from fastapi_versioning import versioned_api_route, version

router = APIRouter(route_class=versioned_api_route(1))


ZOO = dict()


def _idx(l):
    for i in range(l):
        yield i


idx = _idx(100)


@router.post(
    "/pet",
    operation_id="createPet",
    response_model=Pet,
    responses={
        201: {
            "model": Pet,
            "headers": {
                "X-Limit-Remain": {
                    "schema": {"type": "integer"},
                    "required": True,
                    "description": "Remain Request limit for next 60 minutes",
                },
                "X-Limit-Done": {"schema": {"type": "integer"}, "required": False, "description": "Requests done"},
            },
        },
        409: {"model": Error},
    },
)
def createPet(
    response: Response,
    pet: PetCreate = Body(..., embed=True),
) -> None:
    if pet.name in ZOO:
        return JSONResponse(
            status_code=starlette.status.HTTP_409_CONFLICT,
            content=Error(code=errno.EEXIST, message=f"{pet.name} already exists").dict(),
        )
    ZOO[pet.name] = r = Pet(id=next(idx), **pet.dict())
    response.status_code = starlette.status.HTTP_201_CREATED
    response.headers["X-Limit-Remain"] = "5"
    #    response.headers["model"] = r
    return r


@router.get("/pet", operation_id="listPet", response_model=Pets)
def listPet(limit: Optional[int] = None) -> Pets:
    return list(ZOO.values())


@router.get("/pets/{petId}", operation_id="getPet", response_model=Pet, responses={404: {"model": Error}})
def getPet(pet_id: int = Path(..., alias="petId")) -> Pets:
    for k, v in ZOO.items():
        if pet_id == v.id:
            return v
    else:
        return JSONResponse(
            status_code=starlette.status.HTTP_404_NOT_FOUND,
            content=Error(code=errno.ENOENT, message=f"{pet_id} not found").dict(),
        )


@router.delete("/pets/{petId}", operation_id="deletePet", responses={204: {"model": None}, 404: {"model": Error}})
def deletePet(response: Response, pet_id: int = Path(..., alias="petId")) -> Pets:
    for k, v in ZOO.items():
        if pet_id == v.id:
            del ZOO[k]
            response.status_code = starlette.status.HTTP_204_NO_CONTENT
            return response
    else:
        return JSONResponse(
            status_code=starlette.status.HTTP_404_NOT_FOUND,
            content=Error(code=errno.ENOENT, message=f"{pet_id} not found").dict(),
            media_type="application/json; utf-8",
        )
