"""Decision-only adapter around pinned, externally installed official SurFree.

No upstream GPL source is vendored here. The caller supplies its checkout.
All actual queries, including initialization, are counted by an outer oracle.
Returns the smallest-L2 *queried* adversarial, not an unverified candidate.
"""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import numpy as np

UPSTREAM_COMMIT='c9920f2c289a4ad3c2d8d203006bb5964bf71816'
HASHES={
 'surfree.py':'12251b1cf5104921597ed43d58e5631648c3de494538301771b4b90434c2c946',
 'utils/attack.py':'f7184b1704a14e5eeb64092f4ec60e42be97bbc51601f419d3f985651d250a99',
 'utils/dct.py':'6e544171172a21ec430ccd3722e2b08a010388487bcd124dd5862b461f1a3579',
 'utils/utils.py':'c650df59202c301c53b46c0713ff32c3502f25ee6667661a421ebbf4e4ad02ed'}


def load_official(root):
    root=Path(root).resolve()
    for name,digest in HASHES.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('upstream hash mismatch: '+name)
    for name in ('utils','utils.attack','utils.dct','utils.utils'):
        if name in sys.modules:
            paths=list(getattr(sys.modules[name],'__path__',[]))
            source=getattr(sys.modules[name],'__file__',None)
            if source:paths.append(source)
            if not paths or not all(Path(p).resolve().is_relative_to(root) for p in paths):
                raise ValueError('conflicting utils module')
    sys.path.insert(0,str(root))
    try:
        spec=importlib.util.spec_from_file_location('pinned_official_surfree',root/'surfree.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module.SurFree


class QueryBudgetReached(Exception):
    pass


def attack_one(predict_labels,image,label,official_class,*,max_queries=1000,seed=2026,classes=10):
    """predict_labels takes NHWC and returns only integer top-1 class indices.

    Official L2 search, full DCT basis, no quantization. One image at a time
    prevents upstream batched placeholder queries escaping per-image budgets.
    Initialization is capped at min(200, budget-1), counted in total budget.
    """
    import torch
    image=np.asarray(image)
    if image.ndim!=3 or min(image.shape)<1 or not np.issubdtype(image.dtype,np.floating):
        raise ValueError('expected HWC floating image')
    if not np.isfinite(image).all() or image.min()<0 or image.max()>1:
        raise ValueError('image out of bounds')
    if isinstance(max_queries,bool) or not isinstance(max_queries,int) or max_queries<1:
        raise ValueError('positive integer query budget required')
    if not isinstance(seed,int) or seed<0 or not 0<=label<classes:
        raise ValueError('invalid seed or label')
    x=torch.from_numpy(image.astype(np.float32).transpose(2,0,1).copy()).unsqueeze(0)
    best=x.clone();best_pred=None;best_l2=float('inf');queries=0;clean=None;first_success=None
    trace={};init_queries=0

    def oracle(z):
        nonlocal queries,best,best_pred,best_l2,clean,first_success
        if queries>=max_queries:raise QueryBudgetReached()
        if z.shape!=x.shape or not torch.isfinite(z).all() or z.min()<0 or z.max()>1:
            raise ValueError('invalid upstream candidate')
        values=np.asarray(predict_labels(z.detach().cpu().numpy().transpose(0,2,3,1)))
        if values.shape!=(1,) or not np.issubdtype(values.dtype,np.integer) or not 0<=values[0]<classes:
            raise ValueError('oracle must return one integer label')
        pred=int(values[0]);queries+=1
        if clean is None:clean=pred;best_pred=pred
        if pred!=label:
            norm=float(torch.linalg.vector_norm(z-x))
            if norm<best_l2:
                best_l2=norm;best=z.detach().clone();best_pred=pred
            if first_success is None:first_success=queries
        if queries in (200,1000):trace[str(queries)]=None if not np.isfinite(best_l2) else best_l2
        # The official algorithm receives only a label, represented as one-hot.
        return torch.nn.functional.one_hot(torch.tensor([pred]),classes).float()

    with torch.no_grad(),torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        oracle(x)
        reason='clean_misclassified' if clean!=label else 'initialization_failed'
        if clean==label and max_queries>1:
            start=None
            for _ in range(min(200,max_queries-1)):
                candidate=(x+.5*torch.randn_like(x)).clamp(0,1)
                pred=oracle(candidate).argmax(1).item();init_queries+=1
                if pred!=label:start=candidate;break
            if start is not None:
                attack=official_class(steps=max_queries,max_queries=max_queries,
                    BS_gamma=.01,BS_max_iteration=10,rho=.98,T=1,theta_max=30,
                    n_ortho=10,with_distance_line_search=False,with_interpolation=False,
                    with_alpha_line_search=True,quantification=False,final_line_search=True)
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        attack(oracle,x.clone(),torch.tensor([label]),starting_points=start,
                            basis_params=dict(basis_type='dct',dct_type='full',function='constant',frequence_range=[0,.5]))
                    reason='upstream_finished'
                except QueryBudgetReached:
                    reason='query_budget_reached'
    if not np.isfinite(best_l2):
        best_l2=0.;best=x.clone();best_pred=clean
    delta=(best-x).numpy()
    return dict(clean_pred=clean,attacked_pred=best_pred,queries=queries,
        initialization_queries=init_queries,first_success_query=first_success,
        l2=best_l2,linf=float(np.abs(delta).max()),rms=float(np.sqrt(np.mean(delta**2))),
        successful=bool(clean==label and best_pred!=label),stop_reason=reason,
        best_l2_by_total_queries=trace)
