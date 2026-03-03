from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, TextAreaField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, NumberRange
from flask_wtf.file import FileField, FileAllowed, FileRequired

class LoginForm(FlaskForm):
    usuario = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')


class RegisterForm(FlaskForm):
    nombres = StringField('Nombres Completos', validators=[DataRequired(), Length(min=3, max=100)])
    usuario = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Contraseña', 
                                       validators=[DataRequired(), EqualTo('password')])
    rol = SelectField('Rol', choices=[('Analista', 'Analista/Ingeniero')], 
                      validators=[DataRequired()])
    submit = SubmitField('Registrarse')


class InventarioForm(FlaskForm):
    num_proceso = StringField('Número de Proceso', validators=[Optional(), Length(max=50)])
    proveedor = StringField('Proveedor', validators=[Optional(), Length(max=100)])
    material = StringField('Material', validators=[DataRequired(), Length(max=200)])
    descripcion = TextAreaField('Descripción', validators=[Optional(), Length(max=500)])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1)])
    tipo = SelectField('Tipo', choices=[('Herramienta', 'Herramienta'), ('Consumible', 'Consumible'), ('Equipo', 'Equipo'), ('Repuesto', 'Repuesto'), ('Accesorio', 'Accesorio')],
                       validators=[DataRequired()])
    observaciones = TextAreaField('Observaciones', validators=[Optional()])
    submit = SubmitField('Guardar')


class AsignacionForm(FlaskForm):
    id_material = SelectField('Material', coerce=int, validators=[DataRequired()])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1)])
    observaciones = TextAreaField('Observaciones', validators=[Optional()])
    submit = SubmitField('Solicitar')


class AprobacionForm(FlaskForm):
    estatus = SelectField('Estatus', choices=[('Aprobado', 'Aprobar'), ('Rechazado', 'Rechazar')],
                          validators=[DataRequired()])
    observaciones = TextAreaField('Observaciones', validators=[Optional()])
    submit = SubmitField('Guardar')


class ActivarUsuarioForm(FlaskForm):
    activo = SelectField('Estado', choices=[('True', 'Activo'), ('False', 'Inactivo')],
                         validators=[DataRequired()])
    submit = SubmitField('Actualizar')


class ImportForm(FlaskForm):
    archivo = FileField('Archivo Excel (.xlsx)', validators=[
        FileRequired(),
        FileAllowed(['xlsx'], 'Sólo archivos .xlsx')
    ])
    submit = SubmitField('Importar')
