from .base import RuntimeAdapter

class SklearnAdapter(RuntimeAdapter):
    key="sklearn"; family="ML"; libraries=("sklearn",)
    def training_completed(self, context, estimator, metrics=None):
        self.event(context,"ML_MODEL_CREATED",{"estimator":estimator.__class__.__name__})
        for name,value in (metrics or {}).items():
            if isinstance(value,(int,float)): self.metric(context,name,value,scope="evaluation")

class TensorFlowAdapter(RuntimeAdapter):
    key="tensorflow"; family="ML"; libraries=("tensorflow",)
    def epoch_completed(self, context, epoch, total_epochs=None, metrics=None):
        payload={"epoch":epoch,"metrics":metrics or {}}
        if total_epochs is not None: payload["total_epochs"]=total_epochs
        self.event(context,"ML_EPOCH_COMPLETED",payload)
        for name,value in (metrics or {}).items():
            if isinstance(value,(int,float)): self.metric(context,name,value,step=epoch,scope="training")

class PyTorchAdapter(RuntimeAdapter):
    key="pytorch"; family="ML"; libraries=("torch",)
    def epoch_completed(self, context, epoch, total_epochs=None, metrics=None):
        payload={"epoch":epoch,"metrics":metrics or {}}
        if total_epochs is not None: payload["total_epochs"]=total_epochs
        self.event(context,"ML_EPOCH_COMPLETED",payload)
