/****************************************************************************
** Meta object code from reading C++ file 'boardscene.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.12.0)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../projects/gui/src/boardview/boardscene.h"
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'boardscene.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 69
#error "This file was generated using the moc from 6.12.0. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

#ifndef Q_CONSTINIT
#define Q_CONSTINIT
#endif

QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
QT_WARNING_DISABLE_GCC("-Wuseless-cast")
namespace {
struct qt_meta_tag_ZN10BoardSceneE_t {};
} // unnamed namespace

template <> constexpr inline auto BoardScene::qt_create_metaobjectdata<qt_meta_tag_ZN10BoardSceneE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "BoardScene",
        "humanMove",
        "",
        "Chess::GenericMove",
        "move",
        "Chess::Side",
        "side",
        "populate",
        "setFenString",
        "fenString",
        "makeMove",
        "Chess::Move",
        "undoMove",
        "flip",
        "onGameFinished",
        "ChessGame*",
        "game",
        "Chess::Result",
        "result",
        "onTransitionFinished",
        "onPromotionChosen",
        "Chess::Piece",
        "promotion"
    };

    QtMocHelpers::UintData qt_methods {
        // Signal 'humanMove'
        QtMocHelpers::SignalData<void(const Chess::GenericMove &, const Chess::Side &)>(1, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 3, 4 }, { 0x80000000 | 5, 6 },
        }}),
        // Slot 'populate'
        QtMocHelpers::SlotData<void()>(7, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'setFenString'
        QtMocHelpers::SlotData<void(const QString &)>(8, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 9 },
        }}),
        // Slot 'makeMove'
        QtMocHelpers::SlotData<void(const Chess::Move &)>(10, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 11, 4 },
        }}),
        // Slot 'makeMove'
        QtMocHelpers::SlotData<void(const Chess::GenericMove &)>(10, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 3, 4 },
        }}),
        // Slot 'undoMove'
        QtMocHelpers::SlotData<void()>(12, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'flip'
        QtMocHelpers::SlotData<void()>(13, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'onGameFinished'
        QtMocHelpers::SlotData<void(ChessGame *, Chess::Result)>(14, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 15, 16 }, { 0x80000000 | 17, 18 },
        }}),
        // Slot 'onTransitionFinished'
        QtMocHelpers::SlotData<void()>(19, 2, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'onPromotionChosen'
        QtMocHelpers::SlotData<void(const Chess::Piece &)>(20, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 21, 22 },
        }}),
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<BoardScene, qt_meta_tag_ZN10BoardSceneE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject BoardScene::staticMetaObject = { {
    QMetaObject::SuperData::link<QGraphicsScene::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN10BoardSceneE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN10BoardSceneE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN10BoardSceneE_t>.metaTypes,
    nullptr
} };

void BoardScene::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<BoardScene *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->humanMove((*reinterpret_cast<std::add_pointer_t<Chess::GenericMove>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<Chess::Side>>(_a[2]))); break;
        case 1: _t->populate(); break;
        case 2: _t->setFenString((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 3: _t->makeMove((*reinterpret_cast<std::add_pointer_t<Chess::Move>>(_a[1]))); break;
        case 4: _t->makeMove((*reinterpret_cast<std::add_pointer_t<Chess::GenericMove>>(_a[1]))); break;
        case 5: _t->undoMove(); break;
        case 6: _t->flip(); break;
        case 7: _t->onGameFinished((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<Chess::Result>>(_a[2]))); break;
        case 8: _t->onTransitionFinished(); break;
        case 9: _t->onPromotionChosen((*reinterpret_cast<std::add_pointer_t<Chess::Piece>>(_a[1]))); break;
        default: ;
        }
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        switch (_id) {
        default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
        case 0:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::GenericMove >(); break;
            case 1:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Side >(); break;
            }
            break;
        case 4:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::GenericMove >(); break;
            }
            break;
        case 7:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 1:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Result >(); break;
            }
            break;
        }
    }
    if (_c == QMetaObject::IndexOfMethod) {
        if (QtMocHelpers::indexOfMethod<void (BoardScene::*)(const Chess::GenericMove & , const Chess::Side & )>(_a, &BoardScene::humanMove, 0))
            return;
    }
}

const QMetaObject *BoardScene::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *BoardScene::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN10BoardSceneE_t>.strings))
        return static_cast<void*>(this);
    return QGraphicsScene::qt_metacast(_clname);
}

int BoardScene::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QGraphicsScene::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 10)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 10;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 10)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 10;
    }
    return _id;
}

// SIGNAL 0
void BoardScene::humanMove(const Chess::GenericMove & _t1, const Chess::Side & _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 0, nullptr, _t1, _t2);
}
QT_WARNING_POP
