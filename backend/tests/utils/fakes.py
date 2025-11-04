from uuid import uuid4

def fake_uuid() -> str:
    return str(uuid4())

def asdict(model) -> dict:
    # convenient Pydantic/ORM to dict helper
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "__dict__"):
        return {k: v for k, v in model.__dict__.items() if not k.startswith("_")}
    return dict(model)
