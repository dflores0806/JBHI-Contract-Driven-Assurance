from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from .utils import dump_json

FAMILY_ORDER=["nominal","boundary","missing_evidence","conflicting_evidence","explicit_unknown"]


def pct(x):
    return f"{100*x:.1f}\\%"


def ci(m):
    return f"{100*m['ci95_low']:.1f}--{100*m['ci95_high']:.1f}"


def make_tables(df:pd.DataFrame, metrics:dict, out_dir:Path):
    out_dir.mkdir(parents=True,exist_ok=True)
    rows=[]
    for label,key in [("StrokeTwinMentor","twin_stroke"),("LungTwinMentor","twin_lung"),("Overall","overall")]:
        m=metrics[key]
        rows.append(f"{label} & {m['n']} & {m['passed']}/{m['n']} & {pct(m['agreement'])} & {ci(m)} \\\\")
    tex=(
        "\\begin{table}[t]\n"
        "\\caption{Independent synthetic oracle validation. Exact agreement is scenario-level agreement with the frozen pre-execution oracle; CI is Wilson 95\\%.}\n"
        "\\label{tab:cross_implementation}\n"
        "\\centering\n\\footnotesize\n"
        "\\begin{tabular}{lrrrr}\n\\hline\n"
        "Twin & $N$ & Match & Agreement & 95\\% CI \\\\\n"
        "\\hline\n" + "\n".join(rows) + "\n\\hline\n"
        "\\end{tabular}\n\\end{table}\n"
    )
    (out_dir/"cross_implementation_summary.tex").write_text(tex,encoding="utf-8")

    rows=[]
    for fam in FAMILY_ORDER:
        vals=[]
        for twin in ["stroke","lung"]:
            m=metrics["by_family"][f"{twin}:{fam}"]
            vals.append(f"{m['passed']}/{m['n']} ({pct(m['agreement'])})")
        rows.append(f"{fam.replace('_',' ')} & {vals[0]} & {vals[1]} \\\\")
    tex2=(
        "\\begin{table}[t]\n"
        "\\caption{Cross-implementation agreement by scenario family.}\n"
        "\\label{tab:independent_by_family}\n"
        "\\centering\n\\footnotesize\n"
        "\\begin{tabular}{lcc}\n\\hline\n"
        "Family & Stroke & Lung \\\\\n"
        "\\hline\n" + "\n".join(rows) + "\n\\hline\n"
        "\\end{tabular}\n\\end{table}\n"
    )
    (out_dir/"cross_implementation_by_family.tex").write_text(tex2,encoding="utf-8")


def make_macros(metrics:dict,out_path:Path):
    m=metrics["overall"]
    rs=metrics.get("rule_states",{})
    s=(
       f"\\newcommand{{\\IndN}}{{{m['n']}}}\n"
       f"\\newcommand{{\\IndPass}}{{{m['passed']}}}\n"
       f"\\newcommand{{\\IndAgreement}}{{{100*m['agreement']:.1f}\\%}}\n"
       f"\\newcommand{{\\IndCILow}}{{{100*m['ci95_low']:.1f}\\%}}\n"
       f"\\newcommand{{\\IndCIHigh}}{{{100*m['ci95_high']:.1f}\\%}}\n"
       f"\\newcommand{{\\IndMacroFOne}}{{{rs.get('macro_f1',float('nan')):.3f}}}\n"
       f"\\newcommand{{\\IndKappa}}{{{rs.get('kappa',float('nan')):.3f}}}\n"
       f"\\newcommand{{\\IndUnknownRecall}}{{{100*rs.get('unknown_recall',float('nan')):.1f}\\%}}\n"
    )
    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_text(s,encoding="utf-8")


def make_figures(df:pd.DataFrame,metrics:dict,out_dir:Path):
    out_dir.mkdir(parents=True,exist_ok=True)
    agg=df.groupby(["family"])["pass"].mean().reindex(FAMILY_ORDER)
    fig,ax=plt.subplots(figsize=(6.5,3.2))
    ax.barh([x.replace('_',' ') for x in agg.index],100*agg.values)
    ax.set_xlim(0,100)
    ax.set_xlabel("Exact agreement (%)")
    ax.set_ylabel("Scenario family")
    ax.set_title("Cross-implementation agreement by scenario family")
    fig.tight_layout()
    fig.savefig(out_dir/"agreement_by_family.pdf",bbox_inches="tight")
    fig.savefig(out_dir/"agreement_by_family.png",dpi=200,bbox_inches="tight")
    plt.close(fig)

    rs=metrics.get("rule_states")
    if rs:
        cm=np.array(rs["confusion_matrix"])
        labels=rs["labels"]
        fig,ax=plt.subplots(figsize=(4.2,3.8))
        im=ax.imshow(cm)
        ax.set_xticks(range(len(labels)),labels)
        ax.set_yticks(range(len(labels)),labels)
        ax.set_xlabel("System")
        ax.set_ylabel("Reference oracle")
        ax.set_title("Rule-state confusion matrix")
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j,i,str(cm[i,j]),ha='center',va='center')
        fig.colorbar(im,ax=ax,fraction=0.046,pad=0.04)
        fig.tight_layout()
        fig.savefig(out_dir/"rule_state_confusion.pdf",bbox_inches="tight")
        fig.savefig(out_dir/"rule_state_confusion.png",dpi=200,bbox_inches="tight")
        plt.close(fig)


def make_all(df,metrics,root:Path):
    make_tables(df,metrics,root/"outputs/tables")
    make_macros(metrics,root/"outputs/macros/cross_implementation_macros.tex")
    make_figures(df,metrics,root/"outputs/figures")
    df.to_csv(root/"data/runs/case_level_analysis.csv",index=False)
    df[~df["pass"]].to_csv(root/"data/runs/discrepancies.csv",index=False)
    dump_json(root/"data/runs/metrics.json",metrics)
