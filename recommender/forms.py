from django import forms

class CropInputForm(forms.Form):
    N = forms.FloatField(min_value=0, label="Nitrogen (N)")
    P = forms.FloatField(min_value=0, label="Phosphorus (P)")
    K = forms.FloatField(min_value=0, label="Potassium (K)")
    temperature = forms.FloatField(label="Temperature (°C)")
    humidity = forms.FloatField(min_value=0, max_value=100, label="Humidity (%)")
    ph = forms.FloatField(min_value=0, max_value=14, label="Soil pH")
    rainfall = forms.FloatField(min_value=0, label="Rainfall (mm)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({"class": "form-control"})
