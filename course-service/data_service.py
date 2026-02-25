from models import Course

class CourseMockDataService:
    def __init__(self):
        self.courses = [
            Course(id=1, title="Software Engineering", code="SE101", credits=3),
            Course(id=2, title="Data Science", code="DS201", credits=4),
            Course(id=3, title="Microservices", code="MS301", credits=3),
        ]
        self.next_id = 4

    def get_all_courses(self):
        return self.courses

    def get_course_by_id(self, course_id: int):
        return next((c for c in self.courses if c.id == course_id), None)

    def add_course(self, course_data):
        new_course = Course(id=self.next_id, **course_data.model_dump())
        self.courses.append(new_course)
        self.next_id += 1
        return new_course

    def update_course(self, course_id: int, course_data):
        course = self.get_course_by_id(course_id)
        if course:
            update_data = course_data.model_dump(exclude_none=True)
            for k, v in update_data.items():
                setattr(course, k, v)
            return course
        return None

    def delete_course(self, course_id: int):
        course = self.get_course_by_id(course_id)
        if course:
            self.courses.remove(course)
            return True
        return False