# documents/forms.py
from django import forms
from .models import Document, Category
from .models import RefundRequest

DEFAULT_UPLOAD_CATEGORIES = [
    ("Mathematics", "course", "Math notes, revision papers, and assignments"),
    ("Biology", "course", "Biology notes, lab reports, and study guides"),
    ("Chemistry", "course", "Chemistry coursework, labs, and revision materials"),
    ("Physics", "course", "Physics notes, problem sets, and exam prep"),
    ("Computer Science", "course", "Programming, systems, and computing materials"),
    ("Business", "course", "Business, finance, and entrepreneurship documents"),
    ("Accounting", "course", "Accounting notes, ledgers, and exam prep"),
    ("Economics", "course", "Economics coursework, essays, and study materials"),
    ("Finance", "course", "Finance assignments, models, and revision content"),
    ("Marketing", "course", "Marketing plans, notes, and case study material"),
    ("Law", "course", "Law notes, case briefs, and legal research"),
    ("Nursing", "course", "Nursing coursework, clinical notes, and guides"),
    ("Medicine", "course", "Medical notes, study guides, and case materials"),
    ("Pharmacy", "course", "Pharmacy notes, drug references, and revision papers"),
    ("Public Health", "course", "Public health research, reports, and notes"),
    ("Engineering", "course", "Engineering notes, designs, and technical reports"),
    ("Civil Engineering", "course", "Civil engineering calculations, reports, and notes"),
    ("Mechanical Engineering", "course", "Mechanical engineering coursework and diagrams"),
    ("Electrical Engineering", "course", "Electrical engineering notes, labs, and projects"),
    ("Architecture", "course", "Architecture drawings, theory notes, and presentations"),
    ("Education", "course", "Teaching resources, lesson plans, and education notes"),
    ("Psychology", "course", "Psychology notes, experiments, and essays"),
    ("Sociology", "course", "Sociology essays, notes, and research summaries"),
    ("History", "course", "History essays, notes, and reference materials"),
    ("Geography", "course", "Geography fieldwork, maps, and study notes"),
    ("Political Science", "course", "Political science notes, essays, and briefs"),
    ("English", "course", "English literature, grammar, and composition materials"),
    ("Literature", "course", "Literature essays, analysis, and reading notes"),
    ("Linguistics", "course", "Language studies, syntax notes, and phonetics materials"),
    ("Religious Studies", "course", "Religion notes, essays, and comparative study guides"),
    ("Agriculture", "course", "Agriculture notes, practicals, and reports"),
    ("Environmental Science", "course", "Environmental science reports and coursework"),
    ("Statistics", "course", "Statistics worked examples, notes, and revision papers"),
    ("Data Science", "course", "Data science notebooks, notes, and project writeups"),
    ("Past Papers", "exam", "Previous exam papers and marking schemes"),
    ("Mock Exams", "exam", "Practice exams and timed assessment materials"),
    ("Quiz Papers", "exam", "Quiz sheets, class tests, and short assessments"),
    ("Lecture Notes", "notes", "Lecture handouts and student notes"),
    ("Handwritten Notes", "notes", "Scanned handwritten notes and annotated class material"),
    ("Summary Notes", "notes", "Condensed revision summaries and key-point notes"),
    ("Study Guides", "guide", "Revision guides and study support documents"),
    ("Tutorials", "tutorial", "Step-by-step walkthroughs and learning guides"),
    ("Research Papers", "research", "Academic papers and research submissions"),
    ("Assignments", "assignment", "Homework, coursework, and worked solutions"),
    ("Worksheets", "worksheet", "Practice sheets, exercises, and guided activities"),
    ("Presentations", "presentation", "Slides, decks, and presentation materials"),
    ("Thesis", "thesis", "Dissertations, theses, and long-form research"),
    ("Lab Reports", "lab", "Laboratory reports, observations, and experiment writeups"),
    ("Project Reports", "project", "Project documentation, capstones, and reports"),
    ("Textbooks", "textbook", "Book chapters, textbook summaries, and reference extracts"),
    ("Case Studies", "case_study", "Case analyses, scenarios, and applied learning material"),
    ("Syllabus", "syllabus", "Course outlines, unit plans, and module structures"),
    ("Cheat Sheets", "cheat_sheet", "Quick-reference sheets, formulas, and summaries"),
    ("Other", "other", "Any document that does not fit a category above"),
]


def ensure_upload_categories():
    """Make sure the upload category dropdown always has options."""
    existing = Category.objects.filter(is_active=True).order_by("sort_order", "name")
    if existing.exists():
        return existing

    for index, (name, category_type, description) in enumerate(DEFAULT_UPLOAD_CATEGORIES, start=1):
        Category.objects.get_or_create(
            name=name,
            defaults={
                "category_type": category_type,
                "description": description,
                "sort_order": index,
                "is_active": True,
            },
        )

    return Category.objects.filter(is_active=True).order_by("sort_order", "name")

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'title', 'description', 'file', 'price', 'category', 
            'document_type', 'academic_level', 'subject', 'course_code',
            'isbn', 'author', 'university', 'year', 'tags',
            'license_type', 'license_note',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide a detailed description of your document...'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'academic_level': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={'placeholder': 'math, calculus, exam, study guide'}),
            'year': forms.NumberInput(attrs={'placeholder': '2024'}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '9.99'}),
            'license_type': forms.Select(attrs={'class': 'form-select'}),
            'license_note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional: add extra usage terms...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ensure_upload_categories()
        self.fields['category'].empty_label = "Select a category"

    def clean_file(self):
        """Allow uploads of any file type and size accepted by storage."""
        return self.cleaned_data.get('file')

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'title', 'description', 'file', 'price', 'category', 
            'document_type', 'academic_level', 'subject', 'course_code',
            'isbn', 'author', 'university', 'year', 'tags',
            'license_type', 'license_note',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide a detailed description of your document...'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'academic_level': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={'placeholder': 'math, calculus, exam, study guide'}),
            'year': forms.NumberInput(attrs={'placeholder': '2024'}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '9.99'}),
            'license_type': forms.Select(attrs={'class': 'form-select'}),
            'license_note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional: add extra usage terms...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ensure_upload_categories()
        self.fields['category'].empty_label = "Select a category"

        # Explicitly ensure optional metadata fields are not required in the UI.
        for optional_field in ["isbn", "author", "university", "subject", "course_code", "tags", "year", "license_note"]:
            if optional_field in self.fields:
                self.fields[optional_field].required = False

    def clean_file(self):
        """Allow uploads of any file type and size accepted by storage."""
        return self.cleaned_data.get('file')

    def clean_tags(self):
        """Clean and validate tags"""
        tags = self.cleaned_data.get('tags', '')
        if tags:
            # Convert to lowercase and remove extra spaces
            tag_list = [tag.strip().lower() for tag in tags.split(',') if tag.strip()]
            self.cleaned_data['tags'] = ', '.join(tag_list)
        return tags

    def clean_isbn(self):
        """Validate ISBN format"""
        isbn = self.cleaned_data.get('isbn', '')
        if isbn:
            # Remove hyphens and spaces for validation
            isbn_clean = isbn.replace('-', '').replace(' ', '')
            if len(isbn_clean) not in [10, 13] and not isbn_clean.isdigit():
                raise forms.ValidationError("ISBN must be 10 or 13 digits")
        return isbn

    def clean_year(self):
        """Validate year"""
        year = self.cleaned_data.get('year')
        if year and (year < 1900 or year > 2030):
            raise forms.ValidationError("Year must be between 1900 and 2030")
        return year


# Alias for backward compatibility
DocumentUploadForm = DocumentForm


class DocumentSearchForm(forms.Form):
    """Advanced search form for documents"""
    
    SEARCH_TYPES = [
        ('all', 'All Fields'),
        ('title', 'Title Only'),
        ('content', 'Content Only'),
        ('tags', 'Tags Only'),
        ('author', 'Author Only'),
        ('isbn', 'ISBN Only'),
    ]

    query = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search documents...',
            'class': 'form-control-lg'
        })
    )
    
    search_type = forms.ChoiceField(
        choices=SEARCH_TYPES,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="All Categories",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    document_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Document.DOCUMENT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    academic_level = forms.ChoiceField(
        choices=[('', 'All Levels')] + Document.ACADEMIC_LEVELS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    subject = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Mathematics, Biology',
            'class': 'form-control'
        })
    )
    
    course_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., MATH101, BIO202',
            'class': 'form-control'
        })
    )
    
    isbn = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'ISBN (10 or 13 digits)',
            'class': 'form-control'
        })
    )
    
    author = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Author or professor name',
            'class': 'form-control'
        })
    )
    university = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'University or institution',
            'class': 'form-control'
        })
    )
    
    year_min = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'From year',
            'class': 'form-control',
            'min': 1900,
            'max': 2030
        })
    )
    
    year_max = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'To year',
            'class': 'form-control',
            'min': 1900,
            'max': 2030
        })
    )
    
    price_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Min price',
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })
    )
    
    price_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Max price',
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })
    )
    
    tags = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., math, calculus, exam',
            'class': 'form-control'
        })
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('price', 'Price: Low to High'),
            ('-price', 'Price: High to Low'),
            ('title', 'Title: A-Z'),
            ('-title', 'Title: Z-A'),
            ('rating', 'Highest Rated'),
            ('-rating', 'Lowest Rated'),
        ],
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class RefundRequestForm(forms.ModelForm):
    class Meta:
        model = RefundRequest
        fields = ["reason", "details"]
        widgets = {
            "reason": forms.Select(attrs={"class": "form-select"}),
            "details": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Describe the problem...",
                }
            ),
        }
