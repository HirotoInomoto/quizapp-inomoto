from django.contrib import admin
from .models import User ,Quiz, Question, Choice, QuestionAnswer, QuizAnswer, QuizInformation

admin.site.register(User)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(QuestionAnswer)
admin.site.register(QuizAnswer)
admin.site.register(QuizInformation) 