from django.core.management.base import BaseCommand
from documents.models import Category


class Command(BaseCommand):
    help = 'Populate the database with comprehensive document categories'

    def handle(self, *args, **options):
        categories = [
            # Course Materials
            {'name': 'Mathematics', 'category_type': 'course', 'icon': 'bi-calculator', 'description': 'Math courses and materials'},
            {'name': 'Physics', 'category_type': 'course', 'icon': 'bi-lightning', 'description': 'Physics courses and materials'},
            {'name': 'Chemistry', 'category_type': 'course', 'icon': 'bi-droplet', 'description': 'Chemistry courses and materials'},
            {'name': 'Biology', 'category_type': 'course', 'icon': 'bi-dna', 'description': 'Biology courses and materials'},
            {'name': 'Computer Science', 'category_type': 'course', 'icon': 'bi-laptop', 'description': 'Computer science courses and materials'},
            {'name': 'Engineering', 'category_type': 'course', 'icon': 'bi-gear', 'description': 'Engineering courses and materials'},
            {'name': 'Business', 'category_type': 'course', 'icon': 'bi-briefcase', 'description': 'Business courses and materials'},
            {'name': 'Economics', 'category_type': 'course', 'icon': 'bi-graph-up', 'description': 'Economics courses and materials'},
            {'name': 'Literature', 'category_type': 'course', 'icon': 'bi-book', 'description': 'Literature courses and materials'},
            {'name': 'History', 'category_type': 'course', 'icon': 'bi-clock-history', 'description': 'History courses and materials'},
            {'name': 'Psychology', 'category_type': 'course', 'icon': 'bi-person', 'description': 'Psychology courses and materials'},
            
            # Subject Specific
            {'name': 'Algebra', 'category_type': 'subject', 'icon': 'bi-hash', 'description': 'Algebra specific materials'},
            {'name': 'Calculus', 'category_type': 'subject', 'icon': 'bi-infinity', 'description': 'Calculus specific materials'},
            {'name': 'Statistics', 'category_type': 'subject', 'icon': 'bi-bar-chart', 'description': 'Statistics specific materials'},
            {'name': 'Programming', 'category_type': 'subject', 'icon': 'bi-code-slash', 'description': 'Programming specific materials'},
            {'name': 'Data Science', 'category_type': 'subject', 'icon': 'bi-database', 'description': 'Data science specific materials'},
            {'name': 'Machine Learning', 'category_type': 'subject', 'icon': 'bi-robot', 'description': 'Machine learning specific materials'},
            {'name': 'Web Development', 'category_type': 'subject', 'icon': 'bi-globe', 'description': 'Web development specific materials'},
            {'name': 'Mobile Development', 'category_type': 'subject', 'icon': 'bi-phone', 'description': 'Mobile development specific materials'},
            
            # Class Notes
            {'name': 'Lecture Notes', 'category_type': 'notes', 'icon': 'bi-journal-text', 'description': 'Class lecture notes'},
            {'name': 'Study Notes', 'category_type': 'notes', 'icon': 'bi-sticky', 'description': 'Study session notes'},
            {'name': 'Summary Notes', 'category_type': 'notes', 'icon': 'bi-file-text', 'description': 'Summary of key concepts'},
            {'name': 'Handwritten Notes', 'category_type': 'notes', 'icon': 'bi-pencil', 'description': 'Handwritten class notes'},
            
            # Revision Papers
            {'name': 'Past Papers', 'category_type': 'revision', 'icon': 'bi-clock-history', 'description': 'Previous exam papers'},
            {'name': 'Mock Exams', 'category_type': 'revision', 'icon': 'bi-file-earmark-text', 'description': 'Practice exam papers'},
            {'name': 'Quick Revision', 'category_type': 'revision', 'icon': 'bi-lightning', 'description': 'Quick revision materials'},
            {'name': 'Topic Summaries', 'category_type': 'revision', 'icon': 'bi-list-check', 'description': 'Topic-wise summaries'},
            
            # Exam Papers
            {'name': 'Midterm Exams', 'category_type': 'exam', 'icon': 'bi-calendar-check', 'description': 'Midterm examination papers'},
            {'name': 'Final Exams', 'category_type': 'exam', 'icon': 'bi-calendar-event', 'description': 'Final examination papers'},
            {'name': 'Quiz Papers', 'category_type': 'exam', 'icon': 'bi-question-circle', 'description': 'Quiz and test papers'},
            {'name': 'Entrance Exams', 'category_type': 'exam', 'icon': 'bi-door-open', 'description': 'Entrance examination papers'},
            
            # Study Guides
            {'name': 'Exam Guides', 'category_type': 'guide', 'icon': 'bi-map', 'description': 'Exam preparation guides'},
            {'name': 'Study Tips', 'category_type': 'guide', 'icon': 'bi-lightbulb', 'description': 'Study techniques and tips'},
            {'name': 'Subject Guides', 'category_type': 'guide', 'icon': 'bi-compass', 'description': 'Subject-specific guides'},
            {'name': 'Career Guides', 'category_type': 'guide', 'icon': 'bi-briefcase', 'description': 'Career development guides'},
            
            # Reference Materials
            {'name': 'Formulas', 'category_type': 'reference', 'icon': 'bi-calculator', 'description': 'Mathematical and scientific formulas'},
            {'name': 'Tables', 'category_type': 'reference', 'icon': 'bi-table', 'description': 'Reference tables and charts'},
            {'name': 'Dictionaries', 'category_type': 'reference', 'icon': 'bi-book', 'description': 'Subject dictionaries'},
            {'name': 'Encyclopedias', 'category_type': 'reference', 'icon': 'bi-collection', 'description': 'Subject encyclopedias'},
            
            # Lab Reports
            {'name': 'Science Labs', 'category_type': 'lab', 'icon': 'bi-microscope', 'description': 'Science laboratory reports'},
            {'name': 'Computer Labs', 'category_type': 'lab', 'icon': 'bi-pc-display', 'description': 'Computer laboratory reports'},
            {'name': 'Chemistry Labs', 'category_type': 'lab', 'icon': 'bi-droplet', 'description': 'Chemistry laboratory reports'},
            {'name': 'Physics Labs', 'category_type': 'lab', 'icon': 'bi-lightning', 'description': 'Physics laboratory reports'},
            
            # Project Reports
            {'name': 'Final Projects', 'category_type': 'project', 'icon': 'bi-clipboard-check', 'description': 'Final year project reports'},
            {'name': 'Group Projects', 'category_type': 'project', 'icon': 'bi-people', 'description': 'Group project reports'},
            {'name': 'Research Projects', 'category_type': 'project', 'icon': 'bi-search', 'description': 'Research project reports'},
            {'name': 'Capstone Projects', 'category_type': 'project', 'icon': 'bi-trophy', 'description': 'Capstone project reports'},
            
            # Thesis & Dissertations
            {'name': "Bachelor's Thesis", 'category_type': 'thesis', 'icon': 'bi-mortarboard', 'description': "Bachelor's degree thesis"},
            {'name': "Master's Thesis", 'category_type': 'thesis', 'icon': 'bi-journal-text', 'description': "Master's degree thesis"},
            {'name': 'PhD Dissertations', 'category_type': 'thesis', 'icon': 'bi-award', 'description': 'PhD dissertations'},
            {'name': 'Research Papers', 'category_type': 'thesis', 'icon': 'bi-file-earmark-text', 'description': 'Academic research papers'},
            
            # Case Studies
            {'name': 'Business Cases', 'category_type': 'case_study', 'icon': 'bi-briefcase', 'description': 'Business case studies'},
            {'name': 'Medical Cases', 'category_type': 'case_study', 'icon': 'bi-heart-pulse', 'description': 'Medical case studies'},
            {'name': 'Legal Cases', 'category_type': 'case_study', 'icon': 'bi-gavel', 'description': 'Legal case studies'},
            {'name': 'Engineering Cases', 'category_type': 'case_study', 'icon': 'bi-gear', 'description': 'Engineering case studies'},
            
            # Tutorials
            {'name': 'Video Tutorials', 'category_type': 'tutorial', 'icon': 'bi-play-circle', 'description': 'Video-based tutorials'},
            {'name': 'Step-by-Step', 'category_type': 'tutorial', 'icon': 'bi-list-numbered', 'description': 'Step-by-step tutorials'},
            {'name': 'How-To Guides', 'category_type': 'tutorial', 'icon': 'bi-question-circle', 'description': 'How-to guides and tutorials'},
            {'name': 'Workshop Materials', 'category_type': 'tutorial', 'icon': 'bi-people', 'description': 'Workshop and training materials'},
            
            # Syllabus
            {'name': 'Course Syllabus', 'category_type': 'syllabus', 'icon': 'bi-list-ul', 'description': 'Course syllabi and outlines'},
            {'name': 'Exam Syllabus', 'category_type': 'syllabus', 'icon': 'bi-calendar-check', 'description': 'Examination syllabi'},
            {'name': 'Module Outlines', 'category_type': 'syllabus', 'icon': 'bi-grid-3x3', 'description': 'Module and unit outlines'},
            
            # Textbooks
            {'name': 'E-Books', 'category_type': 'textbook', 'icon': 'bi-book', 'description': 'Electronic textbooks'},
            {'name': 'Textbook Chapters', 'category_type': 'textbook', 'icon': 'bi-file-earmark-text', 'description': 'Individual textbook chapters'},
            {'name': 'Reference Books', 'category_type': 'textbook', 'icon': 'bi-bookshelf', 'description': 'Reference and supplementary books'},
            {'name': 'Solution Manuals', 'category_type': 'textbook', 'icon': 'bi-key', 'description': 'Textbook solution manuals'},
            
            # Assignments
            {'name': 'Homework', 'category_type': 'assignment', 'icon': 'bi-house', 'description': 'Homework assignments'},
            {'name': 'Class Projects', 'category_type': 'assignment', 'icon': 'bi-people', 'description': 'Class project assignments'},
            {'name': 'Online Assignments', 'category_type': 'assignment', 'icon': 'bi-globe', 'description': 'Online course assignments'},
            {'name': 'Graded Assignments', 'category_type': 'assignment', 'icon': 'bi-check-circle', 'description': 'Graded assignment solutions'},
            
            # Research Papers
            {'name': 'Journal Articles', 'category_type': 'research', 'icon': 'bi-journal-text', 'description': 'Academic journal articles'},
            {'name': 'Conference Papers', 'category_type': 'research', 'icon': 'bi-mic', 'description': 'Conference presentation papers'},
            {'name': 'Survey Papers', 'category_type': 'research', 'icon': 'bi-pie-chart', 'description': 'Survey research papers'},
            {'name': 'Review Articles', 'category_type': 'research', 'icon': 'bi-search', 'description': 'Literature review articles'},
            
            # Presentations
            {'name': 'PowerPoint', 'category_type': 'presentation', 'icon': 'bi-file-earmark-ppt', 'description': 'PowerPoint presentations'},
            {'name': 'Google Slides', 'category_type': 'presentation', 'icon': 'bi-slides', 'description': 'Google Slides presentations'},
            {'name': 'Keynote', 'category_type': 'presentation', 'icon': 'bi-apple', 'description': 'Keynote presentations'},
            {'name': 'Prezi', 'category_type': 'presentation', 'icon': 'bi-zoom-in', 'description': 'Prezi presentations'},
            
            # Worksheets
            {'name': 'Practice Worksheets', 'category_type': 'worksheet', 'icon': 'bi-pencil-square', 'description': 'Practice exercise worksheets'},
            {'name': 'Math Worksheets', 'category_type': 'worksheet', 'icon': 'bi-calculator', 'description': 'Mathematics worksheets'},
            {'name': 'Language Worksheets', 'category_type': 'worksheet', 'icon': 'bi-translate', 'description': 'Language learning worksheets'},
            {'name': 'Science Worksheets', 'category_type': 'worksheet', 'icon': 'bi-flask', 'description': 'Science experiment worksheets'},
            
            # Cheat Sheets
            {'name': 'Formula Sheets', 'category_type': 'cheat_sheet', 'icon': 'bi-calculator', 'description': 'Mathematical formula cheat sheets'},
            {'name': 'Grammar Cheat Sheets', 'category_type': 'cheat_sheet', 'icon': 'bi-text-paragraph', 'description': 'Grammar and writing cheat sheets'},
            {'name': 'Programming Cheat Sheets', 'category_type': 'cheat_sheet', 'icon': 'bi-code-slash', 'description': 'Programming language cheat sheets'},
            {'name': 'Exam Cheat Sheets', 'category_type': 'cheat_sheet', 'icon': 'bi-file-earmark-text', 'description': 'Exam preparation cheat sheets'},
        ]
        
        created_count = 0
        updated_count = 0
        
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'category_type': cat_data['category_type'],
                    'description': cat_data['description'],
                    'icon': cat_data['icon'],
                    'sort_order': created_count
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created category: {category.name}"))
            else:
                # Update existing categories with new fields
                category.category_type = cat_data['category_type']
                category.description = cat_data['description']
                category.icon = cat_data['icon']
                category.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Updated category: {category.name}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nSummary:"))
        self.stdout.write(self.style.SUCCESS(f"  - Created {created_count} new categories"))
        self.stdout.write(self.style.SUCCESS(f"  - Updated {updated_count} existing categories"))
        self.stdout.write(self.style.SUCCESS(f"  - Total categories: {Category.objects.count()}"))
