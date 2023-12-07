from flask import Flask, request, render_template, redirect, url_for, jsonify, session
import os
from flask_sqlalchemy import SQLAlchemy
import hashlib
from datetime import datetime, timedelta
import jwt
from flask_jwt_extended import (
    create_access_token,
    JWTManager,
    jwt_required,
    get_jwt_identity,
    unset_jwt_cookies,
)

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "database.db"
)


class Config:
    DEBUG = True
    SECRET_KEY = "QWERASDAFDSGSFDS"


app.config.from_object(Config)
jwt = JWTManager(app)
app.config["JWT_COOKIE_SECURE"] = False  # https를 통해서만 cookie가 갈수 있는지 보안망함
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]  # 토큰을 어디서 찾을지 설정
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
    hours=2
)  # 토큰 만료시간 설정 기본은 30분인데 저렇게하면 두시간인가

db = SQLAlchemy(app)


class Member(db.Model):
    mNum = db.Column(db.Integer, primary_key=True, index=True)
    member_id = db.Column(db.String, nullable=False, unique=True)
    pw = db.Column(db.String, nullable=False)
    nickname = db.Column(db.String, nullable=False)

    def __repr__(self):
        return


class Recipe(db.Model):
    rNum = db.Column(db.Integer, primary_key=True, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.mNum"), nullable=True)
    title = db.Column(db.String, nullable=False)
    image = db.Column(db.String, nullable=False)
    ingredient = db.Column(db.String, nullable=False)
    contents1 = db.Column(db.String, nullable=False)
    contents2 = db.Column(db.String, nullable=True)
    contents3 = db.Column(db.String, nullable=True)
    contents4 = db.Column(db.String, nullable=True)
    contents5 = db.Column(db.String, nullable=True)

    def __repr__(self):
        return


class Comment(db.Model):
    cNum = db.Column(db.Integer, primary_key=True, index=True)
    rNum = db.Column(db.ForeignKey("recipe.rNum"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.mNum"), nullable=False)
    contents = db.Column(db.String, nullable=False)

    def __repr__(self):
        return


class Heart(db.Model):
    hNum = db.Column(db.Integer, primary_key=True, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.mNum"), nullable=False)
    rNum = db.Column(db.ForeignKey("recipe.rNum"), nullable=False)

    def __repr__(self):
        return


with app.app_context():
    db.create_all()


@app.route("/")
def main():
    query = Recipe.query.all() + Member.query.all()
    searched_word = request.args.get("words")
    if searched_word:
        word = Recipe.query(searched_word).all()
        db.session.commit()
        return render_template("main.html", data=word)
    else:
        word = []
        return render_template("main.html", data=query)


@app.route("/checkId", methods=["POST"])
def checkId():
    member_id = request.json["member_id"]
    id = Member.query.filter_by(member_id=member_id).first()
    if id is not None:
        return jsonify({"status": "exist"})
    else:
        return jsonify({"status": "available"})


## only 로그인한 회원만!!! 사용 예시입니다.
## @jwt_required()와 get_jwt_identity 사용하시면 됨!
@app.route("/yoururl")
@jwt_required()
def yoururl():
    ## 현재 로그인한 회원의 id를 가져옴.
    member_id = get_jwt_identity()
    print(member_id)
    return render_template("join.html")


@app.route("/join", methods=["GET"])
def ddd():
    return render_template("join.html")


@app.route("/join", methods=["POST"])
def join():
    member_id = request.form.get("member_id")
    pw = request.form.get("pw")
    pw_hash = hashlib.sha256(pw.encode("utf-8")).hexdigest()
    nickname = request.form.get("nickname")
    member = Member(member_id=member_id, pw=pw_hash, nickname=nickname)
    db.session.add(member)
    db.session.commit()
    print("회원가입DB입력완료")
    return render_template("join.html")


@app.route("/login", methods=["GET"])
def dddd():
    return render_template("join.html")


@app.route("/login", methods=["POST"])
def login():
    member_id = request.form.get("member_id")
    pw = request.form.get("pw")
    pw_hash = hashlib.sha256(pw.encode("utf-8")).hexdigest()
    result = Member.query.filter_by(member_id=member_id, pw=pw_hash).first()
    if result is not None:
        # payload = {
        #     'id': member_id,
        #     'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        # }
        access_token = create_access_token(identity=member_id)
        # print(access_token)
        return jsonify({"result": "success", "token": access_token})
    else:
        return jsonify({"message": "아이디와 비밀번호를 다시 확인해주세요."})


@app.route("/protected", methods=["GET"])
@jwt_required()  # 토큰이 인정된 (접근권한이 인정된) 유저만이 이 API를 사용할 수 있다. 유효성 테스트
def protected():
    current_user = get_jwt_identity()  # token으로부터 저장된 데이터를 불러온다
    return jsonify(logged_in_as=current_user), 200


@app.route("/logout", methods=["GET"])
@jwt_required()
def logout():
    resp = jsonify({"message": "로그아웃되었습니다. "})
    unset_jwt_cookies(resp)
    return resp


@app.route("/show/<int:recipeNum>")
def show(recipeNum):
    recipe = Recipe.query.filter_by(rNum=recipeNum).first()
    member = Member.query.filter_by(mNum=recipe.member_id).first()
    comments = Comment.query.filter_by(rNum=recipeNum).all()

    instances = (
        db.session.query(Recipe, Member)
        .join(Member, Member.mNum == Recipe.member_id)
        .all()
    )

    return render_template(
        "showcocktail.html", data=instances, recipe=recipe, comments=comments
    )


@app.route("/comment/<int:recipeNum>", methods=["POST"])
def comment(recipeNum):
    if request.method == "POST":
        comment_text = request.form.get("comment")  # POST 요청에서 댓글 텍스트 가져오기
        # 실제 recipeNum을 사용하여 댓글에 해당하는 Recipe를 찾는다.
        comment = Comment(
            rNum=recipeNum,  # 해당 댓글이 어떤 레시피에 속하는지 식별
            member_id="1",  # 여기에는 실제 사용자 ID를 넣음
            contents=comment_text,
        )
        db.session.add(comment)  # 새 댓글을 데이터베이스에 추가
        db.session.commit()  # 변경 사항 저장

        return redirect(url_for("show", recipeNum=recipeNum))


@app.route("/delete_comment/<int:comment_id>")
def delete_comment(comment_id):
    comment_to_delete = Comment.query.get(comment_id)

    if comment_to_delete:
        # 해당 댓글을 데이터베이스에서 삭제
        db.session.delete(comment_to_delete)
        db.session.commit()

    return redirect(url_for("show", recipeNum=comment_to_delete.rNum))


@app.route("/save", methods=["GET", "POST"])
def recipe_save():
    if request.method == "POST":
        # form에서 보낸 데이터 받아오기
        title_receive = request.form.get("title")
        image_receive = request.form.get("image")
        ingredient_receive = request.form.get("ingredient")
        contents1_receive = request.form.get("contents1")
        contents2_receive = request.form.get("contents2")
        contents3_receive = request.form.get("contents3")
        contents4_receive = request.form.get("contents4")
        contents5_receive = request.form.get("contents5")
        # 데이터를 DB에 저장하기
        recipe = Recipe(
            member_id=0,
            title=title_receive,
            image=image_receive,
            ingredient=ingredient_receive,
            contents1=contents1_receive,
            contents2=contents2_receive,
            contents3=contents3_receive,
            contents4=contents4_receive,
            contents5=contents5_receive,
        )
        db.session.add(recipe)
        db.session.commit()
        return render_template("posting.html")
    elif request.method == "GET":
        return render_template("posting.html")


@app.route("/delete/<int:recipeNum>")
def delete(recipeNum):
    recipe_delete = Recipe.query.get(recipeNum)

    if recipe_delete:
        comments_to_delete = Comment.query.filter_by(rNum=recipeNum).all()
        for comment in comments_to_delete:
            db.session.delete(comment)

        db.session.delete(recipe_delete)
        db.session.commit()

    return redirect(url_for("main"))


@app.route("/edit/<int:recipeNum>", methods=["GET", "POST"])
def edit(recipeNum):
    recipe = Recipe.query.get(recipeNum)

    if request.method == "POST":
        # 폼에서 받은 데이터로 기존 데이터 업데이트
        recipe.title = request.form.get("title")
        recipe.image = request.form.get("image")
        recipe.ingredient = request.form.get("ingredient")
        recipe.contents1 = request.form.get("contents1")
        recipe.contents2 = request.form.get("contents2")
        recipe.contents3 = request.form.get("contents3")
        recipe.contents4 = request.form.get("contents4")
        recipe.contents5 = request.form.get("contents5")

        db.session.commit()  # 변경 사항 저장
        return redirect(url_for("show", recipeNum=recipeNum))  # 수정 후 목록 페이지로 이동

    return render_template("edit.html", recipe=recipe)


if __name__ == "__main__":
    app.run(debug=True)
