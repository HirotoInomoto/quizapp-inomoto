from django.contrib import auth  # 追加
from django.shortcuts import redirect, render  # redirect を追加
from django.contrib.auth import views as auth_views  # 追加
from django.contrib.auth.decorators import login_required # 追加
from django.shortcuts import get_object_or_404, render, redirect  # get_object_or_404 を追加
from .forms import SignUpForm, LoginForm, QuizForm, QuestionForm, ChoiceForm  # QuestionForm, ChoiceForm 追加
from .models import Quiz, Choice,  QuizAnswer, QuestionAnswer, QuizInformation
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Q

def index(request):
    return render(request, "main/index.html")


def signup(request):
    if request.method == "GET":
        form = SignUpForm()
    elif request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password1"]
            user = auth.authenticate(username=username, password=password)
            if user:
                auth.login(request, user)

            return redirect("index")

    context = {"form": form}
    return render(request, "main/signup.html", context)


class LoginView(auth_views.LoginView):
    authentication_form = LoginForm  # ログイン用のフォームを指定
    template_name = "main/login.html"  # テンプレートを指定

def home(request):
    quiz_list = Quiz.objects.filter(user=request.user)
    context = {
        "quiz_list": quiz_list,
    }
    return render(request, "main/home.html", context)


@login_required # ログインしている場合にビュー関数を実行する
def create_quiz(request):
    if request.method == "GET":
        quiz_form = QuizForm()
    if request.method == "POST":
        # 送信内容の取得
        quiz_form = QuizForm(request.POST)
        # 送信内容の検証
        if quiz_form.is_valid():
            quiz = quiz_form.save(commit=False)
            # クイズ作成者を与えて保存
            user = request.user
            quiz.user = user
            quiz.save()
            # 質問作成画面に遷移する
            return redirect("create_question", quiz.id)
    context = {
        "quiz_form":quiz_form,
    }
    return render(request, "main/create_quiz.html", context)

@login_required
def create_question(request, quiz_id):
    if request.method == "GET":
        question_form = QuestionForm()
        choice_form = ChoiceForm()
        quiz = Quiz.objects.get(pk = quiz_id)
        current_question_num = quiz.question_set.all().count()
        next_question_num = current_question_num + 1
    if request.method == "POST":
        # Quiz オブジェクトから id が前画面で作成したオブジェクトの id に等しいものを取得する
        quiz = get_object_or_404(Quiz, id=quiz_id)

        # 送信内容の取得
        question_form = QuestionForm(request.POST)

        # 送られてきたデータの取得
        choices = request.POST.getlist("choice")

        # 正解選択肢の id を取得
        answer_choice_num = request.POST["is_answer"]

        # 送信内容の検証
        if question_form.is_valid():
            question = question_form.save(commit=False)

            # 送信内容を保存する
            question.quiz = quiz
            question.save()

            # Choice モデルにデータを保存する
            for i, choice in enumerate(choices):

                # 正解選択肢には is_answer を True にして保存する
                if i == int(answer_choice_num):
                    Choice.objects.create(question=question, choice=choice, is_answer=True)
                else:
                    Choice.objects.create(question=question, choice=choice, is_answer=False)

            return redirect("create_question", quiz_id)

    context = {
        "question_form":question_form,
        "choice_form":choice_form,
        "quiz_id" : quiz_id,
        "next_question_num" : next_question_num,
    }
    return render(request, "main/create_question.html", context)

def answer_quiz_list(request):
    quiz_list = Quiz.objects.exclude(user=request.user)
    value = ""
    keyword = request.GET.get("keyword")

    # フォームの入力がある場合
    if request.GET.get("keyword"):
        keywords = keyword.split()
        for k in keywords:
            quiz_list = quiz_list.filter(Q(title__icontains=k) | Q(description__icontains=k))
        value = request.GET.get("keyword")
    
    context = {
        "quiz_list": quiz_list,
        "value": value,
    }
    return render(request, "main/answer_quiz_list.html", context)


@login_required
def answer_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    # quiz に紐づく全ての questinon を取得する
    questions = quiz.question_set.all()
    # question オブジェクトの数を集計する
    question_number = questions.count()
    # 得点用の変数を用意する
    score = 0
    user=request.user
    if request.method == "POST":

        for question in questions:
            # 質問ごとにラジオボタンをグループ分けして、質問ごとの選択肢の id を送る」
            choice_id = request.POST.get(str(question.id))
            choice_obj = get_object_or_404(Choice, id=choice_id)
            # 選択した選択肢が正解なら得点を増やす
            if choice_obj.is_answer:
                score += 1
            # 選択した選択肢をデータベースに保存する
            QuestionAnswer.objects.create(user=user, question=question, selected_choice=choice_obj)

        # 得点率を計算する
        answer_rate = score*100/question_number
        # 得点と得点率をデータベースに保存する
        QuizAnswer.objects.create(user=user, quiz=quiz, score=score, answer_rate=answer_rate)

        quiz_answer = QuizAnswer.objects.filter(quiz=quiz)
        whole_average_score = quiz_answer.aggregate(Avg('score'))["score__avg"]
        whole_answer_rate = quiz_answer.aggregate(Avg('answer_rate'))["answer_rate__avg"]

        quiz_information = QuizInformation.objects.filter(quiz=quiz)
        if quiz_information.exists():
            quiz_information.update(
                average_score=whole_average_score,
                answer_rate=whole_answer_rate
                )
        else:
            QuizInformation.objects.create(
                quiz=quiz,
                average_score=whole_average_score,
                answer_rate=whole_answer_rate
                )

        return redirect("result", quiz_id)

    context = {
        "quiz":quiz,
        "questions":questions,
    }
    return render(request, "main/answer_quiz.html", context)

def result(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    # answer = QuizAnswer.objects.filter(user=request.user, quiz=quiz).order_by("-answered_at")[:1]
    # score = answer[0].score
    # rate = answer[0].answer_rate

    answer = QuizAnswer.objects.filter(user=request.user, quiz=quiz).order_by("answered_at").last()

    context = {
        "quiz_answer": answer,
    }
    return render(request, "main/result.html", context)


@login_required
def quiz_information(request, quiz_id):
    quiz = get_object_or_404(Quiz, id = quiz_id)
    try:
        quiz_information = quiz.quizinformation_set.get()
    except QuizInformation.DoesNotExist:
        return render(request, "main/quiz_information.html")
    else:
        quiz_answer_count = quiz.quizanswer_set.all().count()
    context = {
        "quiz_information":quiz_information,
        "quiz_answer_count":quiz_answer_count,
    }
    return render(request, "main/quiz_information.html", context)

class LogoutView(auth_views.LogoutView, LoginRequiredMixin):
    pass