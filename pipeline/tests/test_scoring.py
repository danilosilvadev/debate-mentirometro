from placar.scoring import error_index, mentiromentro


def test_falso_vale_um_e_impreciso_meio():
    index = error_index(verdadeiro=2, impreciso=2, falso=2)
    assert index.total == 6
    assert index.erro == 0.5
    assert index.erro_pct == 50


def test_arredonda_como_o_placar_web():
    thirds = error_index(verdadeiro=1, impreciso=1, falso=1)
    assert (thirds.verdadeiro_pct, thirds.impreciso_pct, thirds.falso_pct) == (33, 33, 33)
    two = error_index(verdadeiro=2, impreciso=0, falso=1)
    assert two.verdadeiro_pct == 67
    assert two.falso_pct == 33


def test_sem_total_fica_em_zero():
    index = error_index(verdadeiro=0, impreciso=0, falso=0)
    assert index.erro == 0
    assert index.erro_pct == 0


def test_ponteiro_so_mexe_com_tres_de_cada_lado():
    reading = mentiromentro(
        left_name="Lula",
        right_name="Flávio Bolsonaro",
        left_verdadeiro=2,
        left_impreciso=0,
        left_falso=0,
        right_verdadeiro=0,
        right_impreciso=0,
        right_falso=10,
    )
    assert reading.ready is False
    assert reading.angle_degrees == 0
    assert reading.headline == "Esperando mais fatos"
    assert "sem dados fica de fora" in reading.basis


def test_cinquenta_pontos_sao_45_graus():
    reading = mentiromentro(
        left_name="A",
        right_name="B",
        left_verdadeiro=3,
        left_impreciso=0,
        left_falso=0,
        right_verdadeiro=2,
        right_impreciso=0,
        right_falso=2,
    )
    assert reading.ready is True
    assert reading.angle_degrees == 45
    assert reading.call.value == "right"


def test_empate_abaixo_de_um_decimo():
    tie = mentiromentro(
        left_name="A",
        right_name="B",
        left_verdadeiro=9,
        left_impreciso=0,
        left_falso=1,
        right_verdadeiro=8,
        right_impreciso=0,
        right_falso=1,
    )
    assert tie.call.value == "tie"
    not_tie = mentiromentro(
        left_name="A",
        right_name="B",
        left_verdadeiro=9,
        left_impreciso=0,
        left_falso=1,
        right_verdadeiro=4,
        right_impreciso=0,
        right_falso=1,
    )
    assert not_tie.call.value != "tie"


def test_singular_de_um_fato():
    reading = mentiromentro(
        left_name="A",
        right_name="B",
        left_verdadeiro=1,
        left_impreciso=0,
        left_falso=0,
        right_verdadeiro=0,
        right_impreciso=0,
        right_falso=3,
    )
    assert "1 fato checável de A" in reading.basis
