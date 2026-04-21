import sys

import mokh


def test_basic(tmp_path):
    path = tmp_path / 'config.yaml'
    path.write_text(
        """
    ch_out: 16
    train: 
        batch_size: 4
    train.lr: 0.02
    """,
        encoding='utf-8',
    )

    @mokh.configurable()
    def setup_model(*, ch_in=16, ch_h=256, ch_out):
        return f'{ch_in=},{ch_h=},{ch_out=}'

    @mokh.configurable()
    def train(model, *, lr=0.01, batch_size=64):
        return f'{model=},{lr=},{batch_size=}'

    sys.argv = ['program.py', '-c', str(path), '-csetup_model.ch_h=128']
    with mokh.configure_cli():
        model = setup_model()
        assert model == 'ch_in=16,ch_h=128,ch_out=16'
        out = train(model)
        assert out == f"model='{model}',lr=0.02,batch_size=4"
        print(model)
        print(out)
