from pydantic import BaseModel, ConfigDict, Field


class Education(BaseModel):
    model_config = ConfigDict(extra="forbid")

    degree: str = Field(description="Degree or qualification explicitly stated in the resume.")
    institution: str = Field(description="Educational institution explicitly stated in the resume.")
    year: str | None = Field(default=None, description="Graduation or attendance year, or null if absent.")


class Experience(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(description="Job title or role explicitly stated in the resume.")
    company: str = Field(description="Employer explicitly stated in the resume.")
    duration: str | None = Field(default=None, description="Employment duration or dates, or null if absent.")
    summary: str | None = Field(default=None, description="Duties or achievements stated for this role, or null if absent.")


class ResumeData(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "phone": None,
                    "skills": ["Python", "FastAPI"],
                    "education": [{"degree": "BSc Computer Science", "institution": "Example University", "year": "2022"}],
                    "experience": [],
                    "summary": None,
                }
            ]
        },
    )

    name: str = Field(description="Person's name stated in the resume; use an empty string if absent.")
    email: str | None = Field(default=None, description="Email address explicitly stated in the resume, or null if absent.")
    phone: str | None = Field(default=None, description="Phone number explicitly stated in the resume, or null if absent.")
    skills: list[str] = Field(default_factory=list, description="Skills explicitly listed or described in the resume.")
    education: list[Education] = Field(default_factory=list, description="Education entries explicitly stated in the resume.")
    experience: list[Experience] = Field(default_factory=list, description="Work experience entries explicitly stated in the resume.")
    summary: str | None = Field(default=None, description="Resume profile or summary explicitly present, or null if absent.")


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(description="Line-item description explicitly shown on the invoice.")
    quantity: float = Field(description="Quantity explicitly shown for this line item.")
    unit_price: float = Field(description="Unit price converted to a number, without a currency symbol.")
    amount: float = Field(description="Line-item amount converted to a number, without a currency symbol.")


class InvoiceData(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "invoice_number": "INV-1001",
                    "invoice_date": "2025-01-15",
                    "vendor_name": "Example Supply",
                    "customer_name": "Acme Ltd",
                    "line_items": [{"description": "Widget", "quantity": 2, "unit_price": 12.5, "amount": 25.0}],
                    "subtotal": 25.0,
                    "tax": 2.5,
                    "total_amount": 27.5,
                    "currency": "USD",
                }
            ]
        },
    )

    invoice_number: str | None = Field(default=None, description="Invoice identifier explicitly stated, or null if absent.")
    invoice_date: str | None = Field(default=None, description="Invoice date as written or normalized, or null if absent.")
    vendor_name: str | None = Field(default=None, description="Seller or supplier name explicitly stated, or null if absent.")
    customer_name: str | None = Field(default=None, description="Bill-to customer name explicitly stated, or null if absent.")
    line_items: list[LineItem] = Field(default_factory=list, description="Invoice line items explicitly stated.")
    subtotal: float | None = Field(default=None, description="Subtotal converted to a number, or null if absent.")
    tax: float | None = Field(default=None, description="Tax amount converted to a number, or null if absent.")
    total_amount: float | None = Field(default=None, description="Invoice total converted to a number, or null if absent.")
    currency: str | None = Field(default=None, description="Currency explicitly indicated by symbol or code, or null if absent.")


class TextRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"text": "Jane Doe | jane@example.com | Python, FastAPI"}]}
    )

    text: str = Field(description="Unstructured resume or invoice text to extract structured data from.")
